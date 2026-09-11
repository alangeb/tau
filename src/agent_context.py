"""Conversation context management for TauErgon.

Core `TauContext` class maintains OpenAI-compatible conversation context with
strict validation for API compliance.

DESIGN INVARIANT: Message alternation is maintained via synthetic bridges.
See designs/DECISIONS.md §18 (Context Management) for the architectural rationale.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from agent_core import TauErgon

from agent_console import (
    _role_color,
    context_validation_warning,
)
from agent_audit_bridge import log_context_add, log_context_remove, log_context_merge, log_context_snapshot
from agent_llm_models import DEFAULT_MAX_CONTEXT_TOKENS, DEFAULT_MAX_OUTPUT_TOKENS
from agent_message_utils import (
    _make_user_prefix,
    _merge_content,
    _sanitize_content,
    _sanitize_text,
    _SYNTHETIC_CATEGORY_TO_TYPE,
    is_synthetic_message,
)
from agent_models import Colors
from agent_context_validation import (
    validate_context,
    validate_on_mutation,
    get_pending_tool_ids as _get_pending_tool_ids,
    validate_tool_resolution as _validate_tool_resolution,
)

# --- Module-level helpers ---

# Fork context markers — short, keyword-prefixed strings placed into tool results
# when preparing a fork's context. Kept concise to save tokens.
_PENDING_TOOL_MARKER = "[PENDING: deferred; resolves after fork. Do not assume result.]"
_FORK_TOOL_MARKER = "[FORK: You are the fork. THIS IS SYNCHRONOUS — you block until complete, then return your result directly. There is NO background execution, NO 'reporting back later'. You are the fork. Task: {task}]"


__all__ = ["TauContext", "ContextMessage", "TauContextInstance"]

ContextMessage: TypeAlias = dict[str, Any]
TauContextInstance: TypeAlias = "TauContext"


def _emit_context_validation_warning(*message_lines: str) -> None:
    """Emit a validation warning to the console."""
    context_validation_warning(list(message_lines))


# ── Merge helpers for merge_consecutive_assistants ──


def _merge_content_field(last: dict, msg: dict) -> None:
    """Merge the 'content' field from *msg* into *last*.

    Handles string, list, and None values. If both are present,
    concatenates via ``_merge_content``. If only *msg* has content,
    copies it. If both are None, leaves *last* unchanged.
    """
    last_content = last.get("content")
    msg_content = msg.get("content")
    if last_content is not None and msg_content is not None:
        last["content"] = _merge_content(last_content, msg_content)
    elif msg_content is not None:
        last["content"] = msg_content


def _merge_string_field(last: dict, msg: dict, field: str) -> None:
    """Merge a string field (e.g. 'reasoning', 'refusal') from *msg* into *last*.

    If both have the field, concatenates via ``_merge_content``.
    If only *msg* has it, copies it.
    """
    if msg.get(field) is not None:
        last_val = last.get(field)
        if last_val is not None:
            last[field] = _merge_content(last_val, msg[field])
        else:
            last[field] = msg[field]


def _merge_tool_calls(last: dict, msg: dict) -> None:
    """Merge tool_calls from *msg* into *last*, deduplicating by ID."""
    if msg.get("tool_calls"):
        if "tool_calls" not in last:
            last["tool_calls"] = []
        existing_ids = {
            tc.get("id") for tc in last["tool_calls"] if tc.get("id")
        }
        for tc in msg.get("tool_calls", []):
            tc_id = tc.get("id")
            if tc_id not in existing_ids:
                last["tool_calls"].append(tc)
                if tc_id:
                    existing_ids.add(tc_id)


def _merge_usage_metadata(last: dict, msg: dict) -> None:
    """Merge usage_metadata from *msg* into *last*, summing numeric values."""
    if msg.get("usage_metadata") is not None:
        if "usage_metadata" not in last:
            last["usage_metadata"] = dict(msg["usage_metadata"])
        else:
            for key, value in msg["usage_metadata"].items():
                if isinstance(value, (int, float)):
                    last["usage_metadata"][key] = (
                        last["usage_metadata"].get(key, 0) + value
                    )
                else:
                    last["usage_metadata"][key] = value


# ── TauContext ────────────────────────────────────────────────────────────────

class TauContext:
    """In-place conversation context with validation after every mutation.

    Each TauErgon owns exactly one instance. Fork metadata is stored separately
    from the message list to avoid polluting conversation history.
    """

    def __init__(self, messages: list[dict] | None = None, nesting_stack: str = "0"):
        self._messages: list[dict] = list(messages) if messages else []
        self._metadata: dict[str, Any] = {}
        self._fork_metadata: dict[str, Any] = {
            "pending_tool_ids": set(),
            "fork_tool_call_id": None,
            "fork_task": None,
        }
        self.nesting_stack: str = nesting_stack
        self._bytes_cache: int = 0       # Cached bytes_size() result
        self._bytes_cache_valid: bool = False  # True if _bytes_cache is up-to-date
        self._validate_on_mutation()

    # --- List protocol ---
    def __len__(self) -> int:
        return len(self._messages)

    def __iter__(self):
        return iter(self._messages)

    def __getitem__(self, idx: int) -> dict:
        return self._messages[idx]

    def __contains__(self, item: Any) -> bool:
        return item in self._messages

    def __repr__(self) -> str:
        return f"TauContext({len(self)} msgs)"

    # --- Metadata ---
    def set_metadata(self, **kwargs) -> None:
        """Set metadata fields for context file save.

        Args:
            **kwargs: Metadata key-value pairs (e.g., pid, working_dir, start_time, model, agent_name).
        """
        self._metadata.update(kwargs)

    def get_metadata(self) -> dict:
        """Return a copy of the context metadata."""
        return dict(self._metadata)

    # --- Validation (delegated to agent_context_validation) ---
    def _validate_on_mutation(self) -> None:
        """Validate context after mutation, printing warnings for errors."""
        validate_on_mutation(self._messages)

    # --- Byte size cache ---
    def _invalidate_bytes(self) -> None:
        """Invalidate the bytes_size() cache. Call after any mutation."""
        self._bytes_cache_valid = False

    def bytes_size(self) -> int:
        """Calculate the size of the serialized context in bytes (cached)."""
        if not self._bytes_cache_valid:
            self._bytes_cache = len(json.dumps(self._messages).encode("utf-8"))
            self._bytes_cache_valid = True
        return self._bytes_cache

    # --- Mutations ---
    def _append(self, msg: dict) -> None:
        """Internal method to append a message to the context."""
        self._messages.append(msg)
        self._invalidate_bytes()
        log_context_add(1, len(self._messages), self.bytes_size())

    def clear(self) -> None:
        """Clear all messages except the system prompt (preserved at index 0)."""
        removed = len(self._messages) - 1  # System prompt preserved
        system = (
            self._messages[0]
            if self._messages and self._messages[0].get("role") == "system"
            else None
        )
        self._messages.clear()
        if system is not None:
            self._messages.append(system)
        self._invalidate_bytes()
        log_context_remove(removed, len(self._messages), self.bytes_size())
        self._validate_on_mutation()

    def extend(self, msgs: list[dict]) -> None:
        """Extend the context by appending multiple messages at once."""
        self._messages.extend(msgs)
        self._invalidate_bytes()
        log_context_add(len(msgs), len(self._messages), self.bytes_size())
        self._validate_on_mutation()

    def append_synthetic_user(self, category: str, content: str) -> None:
        """Append a synthetic user message to the context.

        Synthetic messages are system-injected bridges that maintain valid
        OpenAI message alternation. They are prefixed with [U:TYPE | N:stack]
        so they can be detected and excluded from undo boundaries and
        consecutive-role validation.

        Logs to console (white) and audit for visibility.

        WARNING: If context ends with tool results, use
        `append_synthetic_user_with_bridge()` instead to maintain alternation.

        Args:
            category: The synthetic message category (e.g., 'eot_confirmation').
            content: The message content (without prefix).
        """
        # Map category to type
        user_type = _SYNTHETIC_CATEGORY_TO_TYPE.get(category, "system")
        # Create prefixed content
        prefix = _make_user_prefix(user_type, self.nesting_stack)
        prefixed_content = prefix + _sanitize_text(content)
        # Log synthetic message to console and audit
        from agent_console import synthetic_user
        synthetic_user(category, content)
        self._append({"role": "user", "content": prefixed_content})

    def append_synthetic_user_with_bridge(self, category: str, content: str,
                                           bridge_text: str = "[Processing new input...]") -> None:
        """Append a synthetic user message with an assistant bridge if needed.

        Ensures OpenAI alternation compliance: if the context ends with tool
        results, an assistant message, or a user message, a synthetic assistant
        message is added first. If the context already ends with an assistant
        message (no pending tool calls), the bridge is skipped.

        This is the PREFERRED method for injecting synthetic user messages
        during tool execution. See designs/DECISIONS.md §27.3 (Full bridge requirement).

        Args:
            category: The synthetic message category (e.g., 'parent_inject').
            content: The message content (without prefix).
            bridge_text: Text for the assistant bridge message (default: minimal).
        """
        # Check if context ends with tool results or user message (bridge needed)
        needs_bridge = False
        if self._messages:
            last = self._messages[-1]
            if last.get("role") == "tool":
                needs_bridge = True
            elif last.get("role") == "assistant" and last.get("tool_calls"):
                # Assistant with tool_calls - tool results should follow
                # If they haven't yet, we still need a bridge
                needs_bridge = True
            elif last.get("role") == "user":
                # Context ends with user message — need assistant bridge
                # before appending another (synthetic) user message
                needs_bridge = True

        if needs_bridge:
            # Add synthetic assistant bridge first
            self.append_assistant(bridge_text, synthetic=True)

        # Add synthetic user message
        self.append_synthetic_user(category, content)

    def undo(self) -> None:
        """Undo the last conversation turn by removing messages from the last user message onward.

        Preserves the system message (if present at index 0) and all messages
        up to but not including the last user message.

        Synthetic user messages (marked with SYNTHETIC_PREFIX) are skipped —
        they are system-injected and should not affect undo boundaries.
        """
        if len(self._messages) < 2:
            return
        last_user_idx = None
        for i in range(len(self._messages) - 1, -1, -1):
            msg = self._messages[i]
            if msg.get("role") == "user" and not is_synthetic_message(msg):
                last_user_idx = i
                break
        if last_user_idx is None:
            return
        if last_user_idx == 0 and self._messages[0].get("role") == "system":
            return
        removed = len(self._messages) - last_user_idx
        self._messages = self._messages[:last_user_idx]
        self._invalidate_bytes()
        log_context_remove(removed, len(self._messages), self.bytes_size())
        self._validate_on_mutation()

    # --- Validation (delegated to agent_context_validation) ---
    def validate(self) -> list[str]:
        """Validate the entire context against OpenAI API compliance rules."""
        return validate_context(self._messages)

    # --- Pending state (delegated to agent_context_validation) ---
    def get_pending_tool_ids(self) -> set[str]:
        """Return the set of tool_call_ids that have not yet received a matching tool result."""
        return _get_pending_tool_ids(self._messages)

    def is_tool_pending(self) -> bool:
        """Check if any tool calls in the context are awaiting results."""
        return bool(self.get_pending_tool_ids())

    def validate_tool_resolution(self) -> list[str]:
        """Validate that all tool calls have been resolved with matching tool results."""
        return _validate_tool_resolution(self._messages)

    # --- Token estimation ---
    def estimate_tokens(self, pending_tokens: int = 0) -> int:
        """Estimate the total token count for the context.

        Uses character-based heuristic: ~3 chars per token, 15 tokens structural
        overhead per message.  Multimodal image_url blocks are estimated at
        1120 tokens each (upper-bound for Gemma 4).
        """
        total = 0
        for msg in self._messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 3
            elif isinstance(content, list):
                for part in content:
                    if part.get("type") == "text":
                        total += len(part.get("text", "")) // 3
                    elif part.get("type") == "image_url":
                        total += 1120
            reasoning = msg.get("reasoning", "")
            if isinstance(reasoning, str):
                total += len(reasoning) // 3
            for tc in msg.get("tool_calls") or []:
                args = tc.get("function", {}).get("arguments", "")
                if isinstance(args, str):
                    total += len(args) // 3
            total += 15  # structural overhead (role, IDs, JSON framing)
        total += pending_tokens
        return total

    def get_usage_stats(
        self, max_tokens: int, exact_tokens: int | None = None
    ) -> tuple[int, float, int, bool]:
        """Get comprehensive token usage statistics.

        Returns (token_count, percentage, byte_count, is_exact).
        """
        if exact_tokens is not None and exact_tokens > 0:
            token_count, is_exact = exact_tokens, True
        else:
            token_count, is_exact = self.estimate_tokens(), False
        byte_count = self.bytes_size()
        percentage = token_count / max_tokens if max_tokens > 0 else 0.0
        return token_count, percentage, byte_count, is_exact

    # --- Persistence ---
    def load_from_file(self, context_file: Path) -> bool:
        """Load context messages from a JSON file. Returns True on success.

        Supports both legacy bare-array format and new metadata-wrapped format.
        """
        if not context_file.exists():
            return False
        try:
            with open(context_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "messages" in data:
                # New format with metadata
                if not isinstance(data["messages"], list):
                    return False
                self._metadata = data.get("metadata", {})
                self.set_messages(data["messages"])
            elif isinstance(data, list):
                # Legacy bare-array format
                self.set_messages(data)
            else:
                return False
            return True
        except (json.JSONDecodeError, IOError, TypeError, ValueError):
            self.clear()
            return False

    def save_to_file(self, context_file: Path, force: bool = False) -> bool:
        """Save the current context to a JSON file.

        Writes a metadata block alongside messages for context provenance.
        Skips saving if there are pending tool calls (unless force=True).
        Returns True if file was written, False otherwise.
        """
        pending = self.get_pending_tool_ids()
        if pending and not force:
            return False
        if len(self._messages) < 3:
            return False
        data = {
            "metadata": self._metadata,
            "messages": self._messages,
        }
        with open(context_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True

    # --- Typed append methods ---
    def set_system(self, content: str) -> None:
        """Set the system message for the context. Must be first message."""
        if any(m.get("role") == "system" for m in self._messages):
            raise ValueError(
                "Cannot set system message - system message already exists"
            )
        self._append({"role": "system", "content": _sanitize_text(content)})

    def append_user(self, content: str | list, user_type: str = "real") -> None:
        """Append a user message to the context.

        Emits warnings for invalid sequences (consecutive users, tool->user, etc).

        Args:
            content: The message content (without prefix).
            user_type: The user message type (real, fork, subagent, redirect).
                Defaults to "real" for backward compatibility.
        """
        if not self._messages:
            _emit_context_validation_warning(
                "Attempting to append user message to empty context.",
                "Context should be initialized with set_system() first.",
            )
            return

        last_msg = self._messages[-1]
        last_role = last_msg.get("role")

        if last_role == "assistant" and last_msg.get("tool_calls"):
            _emit_context_validation_warning(
                "Attempting to append user message after assistant with tool calls.",
                "This violates the expected message sequence.",
                "All tool calls should be resolved with tool results first.",
            )
        elif last_role == "tool":
            _emit_context_validation_warning(
                "Attempting to append user message after tool result.",
                "Assistant response should come before next user message.",
            )
        elif last_role == "user":
            _emit_context_validation_warning(
                "Attempting to append consecutive user messages.",
                "Assistant response required between user messages.",
            )
        elif last_role not in ("system", "assistant"):
            _emit_context_validation_warning(
                f"Invalid context state: cannot append user after role '{last_role}'.",
            )

        # Create prefixed content
        prefix = _make_user_prefix(user_type, self.nesting_stack)
        if isinstance(content, str):
            prefixed_content = prefix + _sanitize_content(content)
        else:
            # For list content (multimodal), prefix the text parts
            prefixed_content = [
                {"type": "text", "text": prefix + _sanitize_text(item["text"])}
                if item.get("type") == "text" else item
                for item in content
            ]
        self._append({"role": "user", "content": prefixed_content})

    def append_assistant(
        self,
        content: str | None,
        tool_calls: list[dict] | None = None,
        reasoning: str | None = None,
        synthetic: bool = False,
    ) -> None:
        """Append an assistant message to the context.

        May include content, tool_calls, or both. Emits warnings for invalid sequences.

        Args:
            content: Message content.
            tool_calls: Tool calls (if any).
            reasoning: Reasoning content (if any).
            synthetic: If True, log as synthetic/injected message (white console, audit).
        """
        # Log synthetic assistant messages to console and audit
        if synthetic and content is not None:
            from agent_console import synthetic_assistant
            synthetic_assistant(content)
        if not self._messages:
            _emit_context_validation_warning(
                "Attempting to append assistant message to empty context.",
                "Context should be initialized with set_system() first.",
            )
            return

        last_msg = self._messages[-1]
        last_role = last_msg.get("role")

        if last_role == "assistant":
            # Consecutive assistant messages — insert synthetic bridge
            self.append_synthetic_user("continuation", "Continuing conversation.")
        elif last_role == "system" and len(self._messages) > 1:
            # System → assistant with other messages present — insert bridge
            self.append_synthetic_user("turn_started", "Turn started.")
        elif last_role == "system" and len(self._messages) == 1:
            # Fresh context with only system prompt — insert synthetic user turn
            self.append_synthetic_user("turn_started", "Turn started.")
        elif last_role not in ("user", "tool"):
            # Invalid predecessor — insert bridge to maintain alternation
            self.append_synthetic_user("continuation", "Continuing conversation.")

        msg: dict[str, Any] = {"role": "assistant", "content": _sanitize_content(content) if content is not None else None}
        if tool_calls is not None:
            msg["tool_calls"] = tool_calls
        if reasoning is not None:
            msg["reasoning"] = _sanitize_text(reasoning)
        self._append(msg)

    def append_tool(self, content: str | None, tool_call_id: str) -> None:
        """Append a tool result message to the context.

        Validates tool_call_id references a valid tool call from a preceding
        assistant message.
        """
        if not self._messages:
            _emit_context_validation_warning(
                "Attempting to append tool result to empty context.",
                "Assistant message with tool calls required first.",
            )
            return

        last_msg = self._messages[-1]
        last_role = last_msg.get("role")

        if last_role == "assistant":
            assistant_tool_calls = last_msg.get("tool_calls", [])
            if not assistant_tool_calls:
                _emit_context_validation_warning(
                    "Attempting to append tool result after assistant without tool calls.",
                    "Assistant message must have tool_calls to generate tool results.",
                )
            else:
                valid_ids = {
                    tc.get("id") for tc in assistant_tool_calls if tc.get("id")
                }
                if tool_call_id not in valid_ids:
                    _emit_context_validation_warning(
                        f"Tool result references invalid tool_call_id: '{tool_call_id}'.",
                        f"Valid IDs from assistant: {valid_ids}",
                    )
        elif last_role == "tool":
            # Batch: find most recent assistant to validate tool_call_id
            assistant_idx = next(
                (
                    i
                    for i in range(len(self._messages) - 1, -1, -1)
                    if self._messages[i].get("role") == "assistant"
                ),
                None,
            )
            if assistant_idx is None:
                _emit_context_validation_warning(
                    "No assistant message with tool calls found in context.",
                )
            else:
                valid_ids = {
                    tc.get("id")
                    for tc in self._messages[assistant_idx].get("tool_calls", [])
                    if tc.get("id")
                }
                if tool_call_id not in valid_ids:
                    _emit_context_validation_warning(
                        f"Tool result references invalid tool_call_id: '{tool_call_id}'.",
                        f"Valid IDs from assistant: {valid_ids}",
                    )
        elif last_role == "user":
            _emit_context_validation_warning(
                "Attempting to append tool result after user message.",
                "Assistant must generate tool calls first.",
            )
        elif last_role == "system":
            _emit_context_validation_warning(
                "Attempting to append tool result after system message.",
                "User message and assistant tool calls required first.",
            )
        else:
            _emit_context_validation_warning(
                f"Invalid context state: cannot append tool after role '{last_role}'.",
            )

        func_name = self._get_tool_function_name(tool_call_id) or "unknown_tool"
        self._append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": func_name,
                "content": _sanitize_content(content or ""),
            }
        )

    def _get_tool_function_name(self, tool_call_id: str) -> str | None:
        """Look up the function name for a given tool_call_id from assistant messages."""
        for msg in self._messages:
            if msg.get("role") == "assistant":
                for tc in msg.get("tool_calls", []):
                    if isinstance(tc, dict) and tc.get("id") == tool_call_id:
                        func = tc.get("function", {})
                        if isinstance(func, dict):
                            return func.get("name")
        return None

    # --- Turn management ---
    def cleanup_synthetic(self) -> None:
        """Remove all synthetic messages from the context.

        Synthetic messages are system-injected bridges that maintain OpenAI
        message alternation (see designs/DECISIONS.md §18.5). They should not
        persist across turns, as they are internal-only and never sent to the LLM.

        **Explicit merge design:** This method removes bridges ONLY. It does NOT
        merge consecutive same-role messages. The caller must explicitly invoke
        `merge_consecutive_assistants()` to consolidate any consecutive assistant
        messages left behind.
        This separation prevents hidden mutations: cleanup is pure data removal,
        merge is an explicit policy decision controlled by the caller.

        See designs/DECISIONS.md §18.7 for the rationale.
        """
        removed = sum(1 for m in self._messages if is_synthetic_message(m))
        self._messages = [m for m in self._messages if not is_synthetic_message(m)]
        self._invalidate_bytes()
        if removed:
            log_context_remove(removed, len(self._messages), self.bytes_size())
        # Intentionally NO _validate_on_mutation() here.
        # Removing bridges creates transient consecutive same-role messages.
        # Validation runs after merge_consecutive_assistants() in close_turn().

    def merge_consecutive_assistants(self) -> None:
        """Merge consecutive same-role messages into single messages.

        **Merges assistant and user messages.** After removing synthetic user
        bridges, consecutive assistant messages appear. Consecutive user messages
        can also appear from tool-result / post-parse edge cases. Both are
        merged gracefully (content concatenated) with a warning logged.

        **Consecutive tool messages are allowed** (batched tool calls: one
        assistant message with N tool_calls produces N tool results). They are
        NOT merged — each tool result has a unique tool_call_id/name and must
        be preserved.

        Merge strategy:
        - `content`: concatenated with newline separator
        - `tool_calls`: deduplicated by ID (assistant only)
        - `reasoning`: concatenated with newline separator (assistant only)
        - `refusal`: concatenated with newline separator (assistant only)
        - `usage_metadata`: token counts summed (assistant only)

        NOTE: This is a structural compromise. Merging two independent messages
        into one changes what the LLM sees.  It is necessary because
        cleanup_synthetic() removes the bridges that maintained alternation.
        """
        if len(self._messages) <= 1:
            return

        merged: list[dict] = [dict(self._messages[0])]

        for msg in self._messages[1:]:
            last = merged[-1]
            last_role = last.get("role")
            msg_role = msg.get("role")

            if last_role == msg_role and last_role == "assistant":
                _merge_content_field(last, msg)
                _merge_tool_calls(last, msg)
                _merge_string_field(last, msg, "reasoning")
                _merge_string_field(last, msg, "refusal")
                _merge_usage_metadata(last, msg)
            elif last_role == msg_role and last_role == "tool":
                # Consecutive tool messages are VALID (batched tool calls).
                # Do NOT merge — each has unique tool_call_id/name.
                merged.append(dict(msg))
            elif last_role == msg_role and last_role == "user":
                # Consecutive user messages — merge gracefully.
                _merge_content_field(last, msg)
                from agent_console import warning as _w
                _w(
                    f"merge_consecutive_assistants(): merged consecutive "
                    f"'user' messages — context state was non-alternating. "
                    f"Merged {len(merged)} messages so far."
                )
            elif last_role == msg_role:
                # Any other consecutive same-role — merge as safety net.
                _merge_content_field(last, msg)
                from agent_console import warning as _w
                _w(
                    f"merge_consecutive_assistants(): merged consecutive "
                    f"'{last_role}' messages (unexpected)."
                )
            else:
                merged.append(dict(msg))

        # Log the merge: count = original - merged
        if len(merged) < len(self._messages):
            log_context_merge("assistant", "assistant", len(self._messages) - len(merged))
        self._messages = merged
        self._invalidate_bytes()

    def close_turn(self, reason: str) -> None:
        """Close an incomplete turn to ensure the context ends in a valid terminal state.

        Explicit merge design: cleans up all synthetic messages via cleanup_synthetic(),
        then explicitly merges consecutive assistant messages via merge_consecutive_assistants().
        This two-step approach ensures no hidden mutations: cleanup removes internal-only
        synthetic bridges, merge consolidates the resulting consecutive assistant messages.

        Resolves pending tool calls with the provided reason, then appends an
        assistant message if the last role is user or tool.
        If the last role is "system" or "assistant", inserts a synthetic user
        message first to maintain valid message alternation.

        Idempotent: if context already ends with "assistant" and has no pending
        tool calls, this is a no-op (already in valid terminal state).
        """
        if not self._messages:
            return

        # Clean up synthetic messages before closing the turn.
        # Then explicitly merge consecutive assistant messages left behind.
        # This is the explicit merge design: cleanup_synthetic() removes bridges only;
        # merge_consecutive_assistants() is called explicitly by close_turn() to maintain alternation.
        self.cleanup_synthetic()
        self.merge_consecutive_assistants()
        # Repair: if cleanup removed a synthetic user bridge that was the only separator
        # between system and the first assistant, insert a minimal user message to
        # maintain valid alternation (system → user → assistant).
        # Use synthetic prefix so cleanup_synthetic() can remove it on next close_turn().
        if (
            len(self._messages) >= 2
            and self._messages[0].get("role") == "system"
            and self._messages[1].get("role") == "assistant"
        ):
            prefix = _make_user_prefix("meta", self.nesting_stack)
            self._messages.insert(
                1, {"role": "user", "content": prefix + "[context boundary]"}
            )
        # Validate after merge — cleanup_synthetic() intentionally skips validation
        # because bridge removal creates transient consecutive same-role messages.
        self._validate_on_mutation()

        pending = self.get_pending_tool_ids()
        for tool_id in pending:
            func_name = self._get_tool_function_name(tool_id) or "unknown_tool"
            self.append_tool(reason, tool_id)
            if self._messages and self._messages[-1].get("role") == "tool":
                self._messages[-1]["name"] = func_name

        last_role = self._messages[-1].get("role")

        # Idempotent: if already in valid terminal state (assistant or resolved tool), do nothing
        if last_role == "assistant" and not pending:
            return

        if last_role in ("system", "assistant"):
            # Insert synthetic user message to maintain valid alternation
            self.append_synthetic_user("turn_closed", f"Turn closed: {reason}")
        if self._messages[-1].get("role") in ("user", "tool"):
            self.append_assistant(reason)
        # Invalidate cache for direct mutations (insert, in-place name assignment)
        self._invalidate_bytes()
        # Log context snapshot at turn boundary
        log_context_snapshot(len(self._messages), self.bytes_size(), DEFAULT_MAX_CONTEXT_TOKENS)

    # --- Fork context preparation ---
    def prepare_fork_context(
        self,
        task: str,
        fork_tool_call_id: str | None = None,
        nesting_suffix: str = "",
    ) -> None:
        """Prepare the context for agent forking.

        Marks pending tool calls with FORK/PENDING markers and closes the turn.
        NOT idempotent: caller must deep-copy context before calling.
        """
        if not self._messages:
            self._append({"role": "system", "content": "You are a helpful assistant"})

        self.set_fork_metadata(fork_tool_call_id=fork_tool_call_id, fork_task=task)

        pending = self.get_pending_tool_ids()
        fork_marked = False
        for tid in pending:
            if tid == fork_tool_call_id:
                fork_marked = True
                self.append_tool(_FORK_TOOL_MARKER.format(task=task), tid)
            else:
                self.append_tool(_PENDING_TOOL_MARKER, tid)

        # Warn if fork_tool_call_id was provided but not found in pending calls
        # (covers both: pending exists but ID missing, OR no pending calls at all)
        if fork_tool_call_id is not None and not fork_marked:
            if pending:
                _emit_context_validation_warning(
                    f"fork_tool_call_id '{fork_tool_call_id}' not found in pending "
                    f"tool calls (pending: {sorted(pending)}).",
                    "The fork call will not receive the FORK marker — treating as regular pending.",
                )
            else:
                _emit_context_validation_warning(
                    f"fork_tool_call_id '{fork_tool_call_id}' provided but there are no pending calls to mark.",
                    "The fork call will not receive the FORK marker — treating as regular pending.",
                )

        self.close_turn(f"Turn closed — forking to: {task}{nesting_suffix}")

    # --- Getters / setters ---
    def get_messages(self) -> list[dict]:
        """Return a copy of the internal message list."""
        return self._messages.copy()

    def set_messages(self, msgs: list[dict]) -> None:
        """Replace all messages in the context."""
        self._messages = [self._sanitize_message(m) for m in msgs]
        self._invalidate_bytes()
        self._validate_on_mutation()
    def _sanitize_message(self, msg: dict) -> dict:
        """Sanitize a single message — strips lone UTF-16 surrogates."""
        sanitized = dict(msg)
        if msg.get("content") is not None:
            sanitized["content"] = _sanitize_content(msg["content"])
        if msg.get("reasoning") is not None:
            sanitized["reasoning"] = _sanitize_text(msg["reasoning"])
        return sanitized

    def copy(self) -> TauContext:
        """Create a deep copy of the context (messages only, not fork metadata)."""
        return TauContext(copy.deepcopy(self._messages))

    def get_fork_metadata(self) -> dict:
        """Return a copy of the fork metadata dictionary."""
        return self._fork_metadata.copy()

    def set_fork_metadata(
        self, fork_tool_call_id: str | None = None, fork_task: str | None = None
    ) -> None:
        """Update fork metadata and recompute pending tool IDs."""
        self._fork_metadata["fork_tool_call_id"] = fork_tool_call_id
        self._fork_metadata["fork_task"] = fork_task
        self._fork_metadata["pending_tool_ids"] = self.get_pending_tool_ids()

    def clear_fork_metadata(self) -> None:
        """Reset fork metadata to default empty values."""
        self._fork_metadata = {
            "pending_tool_ids": set(),
            "fork_tool_call_id": None,
            "fork_task": None,
        }

    # --- Compression ---
    def compress(
        self,
        target_percentage: float,
        agent: TauErgon,
        tools: list | None = None,
        last_known_tokens: int | None = None,
        max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    ) -> bool:
        """Compress the context to reduce token usage to a target percentage.

        Uses an LLM to summarize and compress the conversation history.
        """
        from agent_context_compress import compress_context

        try:
            resolved = agent.resolve_group_params()
            compressed_messages, summary, metadata = compress_context(
                self._messages,
                agent.client,
                agent.model_name,
                target_percentage,
                tools or [],
                resolved,
                log_file=agent._session.audit_file,
                audit_writer=agent._session.audit_writer,
                last_known_tokens=last_known_tokens,
                max_context_tokens=max_context_tokens,
                max_output_tokens=max_output_tokens,
            )
            self.set_messages(compressed_messages)
            log_context_snapshot(len(self._messages), self.bytes_size(), max_context_tokens)
            return summary is not None
        except (TypeError, ValueError, KeyError, RuntimeError, OSError):
            return False

    def to_list(self) -> list[dict]:
        """Convert the context to a plain list for JSON serialization.

        Alias of get_messages().
        """
        return self._messages.copy()

    def get_last_assistant(self) -> str | None:
        """Return the text content of the last assistant message, or None.

        Assistant messages are always plain strings (the LLM never returns
        multimodal list content), but we handle the list case defensively.
        """
        for msg in reversed(self._messages):
            if msg.get("role") == "assistant":
                content = msg.get("content")
                if isinstance(content, list):
                    return " ".join(
                        p.get("text", "") for p in content if p.get("type") == "text"
                    )
                return content
        return None

    def get_system(self) -> str | None:
        """Return the system message content (at index 0), or None."""
        if self._messages and self._messages[0].get("role") == "system":
            return self._messages[0].get("content")
        return None

    # --- Context dump ---
    def dump(
        self,
        mode: str = "summary",
        max_tokens: int = 200000,
        exact_tokens: int | None = None,
    ) -> str:
        """Dump the context as a formatted string for display or debugging.

        Modes: summary, full, user, tool, assistant, trace.
        """
        valid_modes = {"summary", "full", "user", "tool", "assistant", "trace"}
        if mode not in valid_modes:
            return (
                f"{Colors.RED}Invalid mode '{mode}'. "
                f"Valid modes: {', '.join(sorted(valid_modes))}{Colors.RESET}"
            )

        if mode == "trace":
            return self._dump_trace()
        if mode == "summary":
            return self._dump_summary(max_tokens, exact_tokens)
        return self._dump_detail(mode)

    def _dump_summary(
        self, max_tokens: int = 200000, exact_tokens: int | None = None
    ) -> str:
        """Generate a compact summary of the context with truncated content and usage stats."""
        lines = []
        token_count, percentage, byte_count, is_exact = self.get_usage_stats(
            max_tokens, exact_tokens
        )
        token_display = f"{token_count:,}" if is_exact else f"~{token_count:,}"

        lines.append(f"\n{'=' * 60}")
        lines.append(f"CONTEXT SUMMARY ({len(self)} messages)")
        lines.append(
            f"Tokens: {token_display} ({percentage:.1%} of {max_tokens:,} max)"
        )
        lines.append(f"Bytes: {byte_count:,}")
        lines.append(f"{'=' * 60}")
        lines.append("")

        for i, msg in enumerate(self._messages):
            role = msg.get("role", "unknown")
            content = msg.get("content") or ""
            if isinstance(content, list):
                image_count = sum(1 for p in content if p.get("type") == "image_url")
                text_parts = [p.get("text", "") for p in content if p.get("type") == "text"]
                content_str = f"[{image_count} image(s), {len(text_parts)} text block(s)]"
                if text_parts:
                    content_str += ": " + text_parts[0][:80]
            else:
                content_str = str(content)
            if len(content_str) > 100:
                content_str = content_str[:100] + "..."
            tool_calls = msg.get("tool_calls")
            tool_info = ""
            if tool_calls:
                tool_names = [
                    tc.get("function", {}).get("name", "?") for tc in tool_calls
                ]
                tool_info = f" [tools: {', '.join(tool_names)}]"
            color = _role_color(role)
            lines.append(
                f"{color}{i + 1}. [{role}]{tool_info} {content_str}{Colors.RESET}"
            )
        lines.append(Colors.RESET)
        return "\n".join(lines)

    def _dump_detail(self, mode: str) -> str:
        """Generate a detailed view of the context filtered by message role."""
        role_map = {
            "user": "user",
            "tool": ("tool", "tool_call"),
            "assistant": "assistant",
        }
        target = role_map.get(mode, None)
        if target:
            if isinstance(target, tuple):
                messages = [
                    (i, m)
                    for i, m in enumerate(self._messages)
                    if m.get("role") in target
                ]
            else:
                messages = [
                    (i, m)
                    for i, m in enumerate(self._messages)
                    if m.get("role") == target
                ]
            title = f"{mode.upper()} MESSAGES ONLY ({len(messages)} messages)"
        else:
            messages = list(enumerate(self._messages))
            title = f"CONTEXT ({len(messages)} messages)"

        lines = [f"\n{Colors.CYAN}{title}{Colors.RESET}"]
        for idx, (_, msg) in enumerate(messages):
            role = msg.get("role", "unknown")
            content = str(msg.get("content") or "(none)")
            lines.append(f"\n--- Message {idx + 1} [{role}] ---")
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                tc_lines = []
                for j, tc in enumerate(tool_calls):
                    name = tc.get("function", {}).get("name", "?")
                    args = tc.get("function", {}).get("arguments", "")
                    args_display = args if mode == "full" else (
                        args[:100] + ("..." if len(str(args)) > 100 else "")
                    )
                    tc_lines.append(
                        f"    {j + 1}. {name}({args_display})"
                    )
                lines.append(
                    f"{content}{Colors.CYAN}\n{''.join(tc_lines)}{Colors.RESET}"
                )
            else:
                lines.append(f"{content}{Colors.RESET}")
        lines.append(Colors.RESET)
        return "\n".join(lines)

    def _dump_trace(self) -> str:
        """Generate a debug trace view of the context with detailed formatting."""
        lines = []
        reset = Colors.RESET
        white = reset  # SYST, USER
        green = Colors.GREEN  # ASSI
        cyan = Colors.CYAN  # TOOL, tool call blocks
        yellow = Colors.YELLOW  # Pending indicator

        total = len(self._messages)
        width = max(3, len(str(total)))

        lines.append(f"\n{white}{'=' * 60}{reset}")
        lines.append(f"{white}CONTEXT TRACE (full){reset}")
        lines.append(f"{white}{'=' * 60}{reset}")

        # Show pending tool calls
        pending = self.get_pending_tool_ids()
        if pending:
            lines.append(f"{yellow}PENDING TOOL CALLS:{reset} {pending}")

        # Show validation errors
        errors = self.validate()
        if errors:
            lines.append(f"{Colors.RED}VALIDATION ERRORS ({len(errors)}):{reset}")
            for err in errors:
                lines.append(f"  {Colors.RED}- {err}{reset}")

        lines.append(f"{'─' * 60}")

        # Build tool_id -> tool result lookup (for inline linking)
        tool_id_to_result = {}
        for msg in self._messages:
            if msg.get("role") == "tool":
                tid = msg.get("tool_call_id", "")
                result_content = msg.get("content", "")
                if isinstance(result_content, str):
                    tool_id_to_result[tid] = result_content[:120] + (
                        "..." if len(str(result_content)) > 120 else ""
                    )
                else:
                    tool_id_to_result[tid] = str(result_content)[:120]

        # Show ALL messages from start to end
        for idx, msg in enumerate(self._messages):
            role = msg.get("role", "unknown")
            content = msg.get("content")
            if content is None:
                content = ""
            if isinstance(content, list):
                image_count = sum(1 for p in content if p.get("type") == "image_url")
                text_parts = [p.get("text", "") for p in content if p.get("type") == "text"]
                content_str = f"[{image_count} image(s), {len(text_parts)} text block(s)]"
                if text_parts:
                    content_str += ": " + text_parts[0][:80]
            else:
                content_str = str(content)

            # Format message number: right-aligned, 3 characters minimum
            num_str = f"{idx + 1:>{width}}"

            if role == "system":
                clean = content_str.replace("\n", " ").replace("\r", " ")
                if len(clean) > 120:
                    clean = clean[:120] + "..."
                lines.append(f"\n{white}{num_str} [SYST] {clean}{reset}")

            elif role == "user":
                clean = content_str.replace("\n", " ").replace("\r", " ")
                if len(clean) > 120:
                    clean = clean[:120] + "..."
                lines.append(f"\n{white}{num_str} [USER] {clean}{reset}")

            elif role == "assistant":
                clean = content_str.replace("\n", " ").replace("\r", " ")
                if len(clean) > 120:
                    clean = clean[:120] + "..."

                tc = msg.get("tool_calls")
                if tc:
                    lines.append(f"\n{green}{num_str} [ASSI] {clean}{reset}")

                    for tool_call in tc:
                        tc_id = tool_call.get("id", "NO-ID")
                        func = tool_call.get("function", {})
                        tool_name = func.get("name", "unknown")
                        tool_args = func.get("arguments", "")

                        params = []
                        if tool_args:
                            try:
                                args_dict = json.loads(tool_args) if tool_args else {}
                                for k, v in args_dict.items():
                                    v_str = str(v)[:80]
                                    params.append(f"{k}={v_str}")
                            except (
                                json.JSONDecodeError,
                                ValueError,
                                TypeError,
                                KeyError,
                            ):
                                params.append(tool_args[:80])

                        param_str = ", ".join(params) if params else tool_args[:80]

                        lines.append(f"{cyan}└─ [{tool_name}] id={tc_id}{reset}")
                        if param_str:
                            lines.append(f"{cyan}    {param_str}{reset}")

                        if tc_id in tool_id_to_result:
                            result_preview = tool_id_to_result[tc_id]
                            lines.append(f"{cyan}    → result: {result_preview}{reset}")
                        else:
                            lines.append(f"{yellow}    → result: PENDING{reset}")
                else:
                    lines.append(f"\n{green}{num_str} [ASSI] {clean}{reset}")

            elif role == "tool":
                tc_id = msg.get("tool_call_id", "NO-ID")
                result_content = content_str[:120] + (
                    "..." if len(content_str) > 120 else ""
                )
                lines.append(f"\n{cyan}{num_str} [TOOL] id={tc_id}{reset}")
                lines.append(f"{cyan}    {result_content}{reset}")

            else:
                preview = content_str[:120] + ("..." if len(content_str) > 120 else "")
                lines.append(f"\n{white}{num_str} [{role.upper()}] {preview}{reset}")

        lines.append(f"\n{'─' * 60}")
        lines.append(f"{white}END TRACE{reset}")
        return "\n".join(lines)
