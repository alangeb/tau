"""Accidental end-of-turn (EOT) protection mechanism.

Extracted from TauErgon to isolate the EOT confirmation logic into its own
class. This module handles:

- Detecting when the LLM returns plain text without tool calls
- Injecting synthetic confirmation requests
- Parsing sentinel responses
- Rewinding confirmation rounds when the LLM returns tool calls
- Accepting confirmed EOT and closing the turn

The sentinel string is assembled from parts at runtime to prevent the LLM
from pattern-matching the exact sentinel in its training data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_audit_writer import AuditWriter
    from agent_context import TauContext
    from agent_core import TauErgon


# ── Sentinel constants ───────────────────────────────────────────────────────
# Assembled from parts to prevent LLM pattern learning.

_ACCIDENTAL_EOT_PREFIX = "ENDOFTURN"
_ACCIDENTAL_EOT_BUDGET = 20  # Max accidental EOT confirmations before forced end

# Single sentinel — assembled at module load time.
ACCIDENTAL_EOT = _ACCIDENTAL_EOT_PREFIX  # "ENDOFTURN"

__all__ = [
    "EOTProtection",
    "ACCIDENTAL_EOT",
    "_ACCIDENTAL_EOT_PREFIX",
    "_ACCIDENTAL_EOT_BUDGET",
]


# ── Malformed tool-call detection ────────────────────────────────────────────

# Patterns that indicate a malformed tool-call attempt (not a valid response).
# These are XML-like or backtick-wrapped tool invocations that postparse
# didn't extract as valid tool calls.
_MALFORMED_TOOL_CALL_PATTERNS = [
    # Backtick-wrapped tool names: `glob`, `bash`, `file_read`, etc.
    r"^`[a-z_]+`$",
    r"^`[a-z_]+\s",  # `tool arg...`
    # XML-style invocations: <invoke name="...">, <call name="...">
    r"^<invoke\s+name=",
    r"^<call\s+name=",
    # XML-style with parameters: <call name="..." parameters="...">
    r"^<call\s+name=.*parameters=",
    # Self-closing XML: <bash .../>, <call .../>
    r"^<[a-z_]+\s+[^>]*/>$",
    # XML-style with cmd attribute: <bash cmd="...">
    r"^<[a-z_]+\s+cmd=",
    # Function-style: <function name="...">
    r"^<function\s+name=",
    # Code block with tool-like content: ```bash\n...
    r"^```[a-z_]+\s*$",
]

import re as _re

_MALFORMED_RE = [_re.compile(p) for p in _MALFORMED_TOOL_CALL_PATTERNS]


def _looks_like_malformed_tool_call(text: str) -> bool:
    """Check if text looks like a malformed tool-call pattern.

    Returns True if the text appears to be a tool-call attempt that
    postparse didn't extract (e.g., backtick-wrapped tool names,
    XML-style invocations). Returns False for normal text responses.
    """
    if not text:
        return False
    # Check the first line (malformed patterns typically start on line 1)
    first_line = text.split("\n")[0]
    for pattern in _MALFORMED_RE:
        if pattern.search(first_line):
            return True
    return False


# ── EOTProtection class ──────────────────────────────────────────────────────

class EOTProtection:
    """Manages accidental end-of-turn protection for the agent.

    When the LLM returns plain text without tool calls, this class:
    1. Holds the message on a confirmation stack
    2. Injects a synthetic user message asking for confirmation
    3. Parses the LLM's response for sentinel strings
    4. Either accepts the EOT or rewinds with tool calls

    The class maintains its own state (counter, stack) and operates on
    the provided context and audit writer.
    """

    def __init__(
        self,
        agent: TauErgon,
    ) -> None:
        """Initialize EOT protection.

        Args:
            agent: The TauErgon agent instance. Provides context, audit_writer,
                and last_substantive_response via live reference (not a snapshot).
        """
        self._agent = agent

        # State — reset at the start of each turn
        self._accidental_eot_counter: int = 0
        self._eot_confirmation_stack: list[dict] = []

    @property
    def _context(self) -> TauContext:
        """Live reference to agent's context (not a snapshot)."""
        return self._agent.context

    @property
    def _audit_writer(self) -> "AuditWriter":
        """Live reference to agent's audit writer (not a snapshot)."""
        return self._agent._session.audit_writer

    @property
    def is_in_confirmation(self) -> bool:
        """Return True if currently in a confirmation round."""
        return bool(self._eot_confirmation_stack)

    @property
    def counter(self) -> int:
        """Return the current accidental EOT counter."""
        return self._accidental_eot_counter

    @property
    def stack(self) -> list[dict]:
        """Return a copy of the confirmation stack (for testing and inspection)."""
        return list(self._eot_confirmation_stack)

    def set_latest_text(self, text: str) -> None:
        """Update the text of the latest held message on the stack.

        Used when the LLM's response contains both a sentinel and tool calls.
        The sentinel is stripped and the preceding content becomes the new text.
        """
        if self._eot_confirmation_stack:
            self._eot_confirmation_stack[-1]["text"] = text

    def reset(self) -> None:
        """Reset EOT state at the start of each turn."""
        self._accidental_eot_counter = 0
        self._eot_confirmation_stack = []

    # ── Confirmation checking ────────────────────────────────────────────────

    def check_confirmation(
        self, response_text: str | None
    ) -> tuple[bool, str | None]:
        """Check if the LLM's response contains the EOT confirmation sentinel.

        When we're in a confirmation round, the LLM may reply with the sentinel
        string (assembled from parts) to confirm EOT. This method checks the
        response and returns whether confirmation was found.

        Also accepts responses that end with the sentinel as the last full word,
        stripping the sentinel and using the preceding content as the response.

        Args:
            response_text: The LLM's response text to check.

        Returns:
            A tuple of (confirmed, stripped_text):
            - confirmed: True if the sentinel was found, False otherwise.
            - stripped_text: The response text with the sentinel stripped from
              the end, or None if exact match, or the original text if no match.
        """
        if not response_text:
            return (False, response_text)
        text = response_text.strip()
        # Check for exact sentinel match (case-insensitive)
        if text.upper() == ACCIDENTAL_EOT.upper():
            return (True, None)
        # Check if response ends with sentinel as the last full word.
        # Strip the sentinel from the end and accept the preceding content.
        if text.upper().endswith(ACCIDENTAL_EOT.upper()):
            # Extract content before the sentinel
            before = text[: len(text) - len(ACCIDENTAL_EOT)].rstrip()
            if before:  # Must have content before the sentinel
                return (True, before)
        return (False, text)

    # ── Handle potential EOT ─────────────────────────────────────────────────

    def handle_potential_eot(
        self,
        response_text: str | None,
        reasoning_content: str | None,
    ) -> None:
        """Handle a potential end-of-turn: hold message, inject confirmation request.

        When the LLM returns plain text without tool calls, we hold the message
        on the confirmation stack and inject a synthetic user message asking the LLM
        to confirm completion or continue with more tool calls.

        The confirmation message includes sentinel strings (assembled from parts)
        that the LLM can use to confirm. The LLM may also simply continue with
        tool calls, in which case we rewind and process them.

        If called again while already in a confirmation round (stack not empty),
        we stack another confirmation layer — the LLM's response is held on the
        stack and another synthetic user message is appended. This allows the
        LLM to be asked repeatedly without losing previous context.

        Note: Sentinel strings are assembled from parts (prefix + suffix) to
        prevent the LLM from pattern-matching the exact sentinel in its training.
        This also means the LLM can freely edit the response text (e.g., via
        file_edit, thinking tags, tool call tags) without accidentally producing
        a sentinel string — the parts are never adjacent in the model's context.
        """
        # Import here to avoid circular dependency at module load
        from agent_message_utils import get_last_real_user_prompt

        # Hold the message on the stack
        self._eot_confirmation_stack.append({
            "text": response_text,
            "reasoning": reasoning_content,
        })

        # --- Audit: log confirmation request ---
        held_preview = (response_text or "")[:80].replace("\n", " ")
        self._audit_writer._emit(
            "EOT_CONFIRM_REQUEST",
            f"stack_depth={len(self._eot_confirmation_stack)} held_preview={held_preview!r}"
        )
        from agent_console import status as _status
        _status(
            f"[EOT] Asking LLM to confirm end-of-turn "
            f"(stack depth: {len(self._eot_confirmation_stack)})"
        )

        # Append the assistant response to context (preserves alternation invariant)
        # This must happen BEFORE the synthetic user message so that
        # pop_all_confirmations can correctly unwind the pair.
        if response_text is not None:
            self._context.append_assistant(response_text, reasoning=reasoning_content)

        # Get the last real user prompt for context
        last_real_prompt = get_last_real_user_prompt(self._context.get_messages())

        # Build confirmation request with sentinel string.
        # Sentinel is assembled from parts to prevent pattern learning.
        sentinel = ACCIDENTAL_EOT

        # Use the latest held response text (top of stack)
        held_text = self._eot_confirmation_stack[-1].get("text", "")

        synthetic_content = (
            f"CONFIRMATION REQUEST: You just sent a plain text response. "
            f"Confirm you are finished with the task below and your answer is the response you just sent.\n\n"
            f"The original user prompt was <ORIGINALUSERPROMPT>{last_real_prompt}</ORIGINALUSERPROMPT>.\n\n"
            f"Your last assistant message was <LASTREPLY>{held_text}</LASTREPLY>.\n\n"
            f"To confirm, reply with ONLY the text \"{sentinel}\" as your assistant message content. "
            f"IMPORTANT: Just type the sentinel word as plain text — do NOT use a tool call, do NOT run bash echo. "
            f"Your assistant content should be ONLY the sentinel word, nothing else. "
            f"If you confirm, LASTREPLY will be reported back. "
            f"Otherwise just continue to work (with your next tool calls)."
        )

        self._context.append_synthetic_user("eot_confirmation", synthetic_content)

    # ── Pop confirmations ────────────────────────────────────────────────────

    def pop_all_confirmations(self) -> None:
        """Pop all EOT confirmation layers from the context.

        Removes all synthetic user messages (confirmation requests) AND their
        corresponding assistant responses (LLM's plain text) from the context.
        After popping, the context should be back to the state before the
        first EOT confirmation was injected.

        Robustness notes:
        - This method assumes the context alternation invariant holds: each
          handle_potential_eot() call appends exactly one assistant message
          followed by one synthetic user message. If the context has been
          modified between handle_potential_eot() and pop_all_confirmations()
          (e.g., by compression, error recovery, or external intervention),
          the role/content checks may fail and leave the stack inconsistent.
        - The method uses a "best effort" approach: it pops message pairs while
          the roles match expectations, and stops on the first mismatch.
          A mismatch leaves the stack in an inconsistent state — the caller
          should handle this gracefully (e.g., by clearing the stack and
          continuing).
        - Future improvement: track message IDs or use a more robust mechanism
          (e.g., marking messages with a unique token) to avoid relying on
          role/content pattern matching.
        """
        msgs = self._context._messages
        # Pop pairs: (synthetic user confirmation, assistant response)
        # Each stack entry corresponds to one assistant response + one synthetic user message.
        # Note: handle_potential_eot appends assistant FIRST, then synthetic user,
        # so msgs[-1] is the synthetic user, and msgs[-2] is the assistant.
        for _ in self._eot_confirmation_stack:
            if len(msgs) >= 2:
                # Pop the synthetic user confirmation first (it's at the end)
                if msgs[-1].get("role") == "user":
                    content = msgs[-1].get("content", "")
                    if "[U:confirm | N:" in str(content):
                        msgs.pop()
                    else:
                        # Not our synthetic — context may be corrupted
                        break
                # Pop the assistant response (LLM's plain text response)
                if msgs[-1].get("role") == "assistant":
                    msgs.pop()
                else:
                    # Assistant not found — context may be corrupted
                    break
            elif len(msgs) == 1:
                # Only one message left — check if it's our synthetic
                if msgs[-1].get("role") == "user":
                    content = msgs[-1].get("content", "")
                    if "[U:confirm | N:" in str(content):
                        msgs.pop()
        # Clear the stack
        self._eot_confirmation_stack.clear()

    def pop_synthetic_only(self) -> None:
        """Pop only synthetic user confirmation messages (not assistant responses).

        Used before slash command dispatch during a confirmation round. Unlike
        pop_all_confirmations, this preserves the assistant messages so that
        the context ends with assistant (allowing command handler to append
        user + assistant without consecutive-user violation).

        Removes ALL synthetic user confirmations from the context, not just
        the ones at the end. This handles interleaved assistant/synthetic
        message patterns from stacked confirmation rounds.
        """
        msgs = self._context._messages
        # Remove all synthetic user confirmations
        self._context._messages = [
            m for m in msgs
            if not (m.get("role") == "user" and "[U:confirm | N:" in str(m.get("content", "")))
        ]
        # Clear the stack
        self._eot_confirmation_stack.clear()

    # ── Rewind with tool calls ───────────────────────────────────────────────

    def rewind_with_tools(
        self,
        tool_calls: list[dict],
        reasoning_content: str | None,
    ) -> None:
        """Rewind from a confirmation round: LLM returned tool calls.

        When the LLM returns tool calls during an EOT confirmation round:
        1. Pop the LLM's response (assistant message)
        2. Pop all synthetic user confirmation messages
        3. Pop all assistant responses (held messages)
        4. Append the held potential EOT message with tool calls
        5. The message is no longer an EOT (it has tool calls)

        This keeps context clean — the model never sees the confirmation exchange.
        Uses append_assistant() for proper synthetic bridge handling.
        """
        # Save the latest held message BEFORE clearing (matches what LASTREPLY showed)
        held = self._eot_confirmation_stack[-1] if self._eot_confirmation_stack else None

        # Pop the LLM's response (assistant message) BEFORE calling
        # pop_all_confirmations(). Same reasoning as accept_confirmation().
        msgs = self._context._messages
        if msgs and msgs[-1].get("role") == "assistant":
            msgs.pop()

        # Pop all confirmation layers (clears the stack)
        self.pop_all_confirmations()

        # Convert executor-format tool calls to OpenAI format for context storage
        openai_tool_calls = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc.get("args", ""),
                },
            }
            for tc in tool_calls
        ]

        # Append the held message with tool calls via proper context method
        # append_assistant() handles synthetic bridges if needed
        if held:
            self._context.append_assistant(
                held.get("text"),
                reasoning=held.get("reasoning"),
                tool_calls=openai_tool_calls,
            )

    # ── Accept confirmation ──────────────────────────────────────────────────

    def accept_confirmation(self) -> str:
        """Accept an EOT confirmation: close turn with best available response.

        Response selection priority:
        1. last_substantive_response (most recent valid plain text response)
        2. held message from confirmation stack (if not malformed)
        3. Empty string (fallback)

        last_substantive_response is updated on EVERY valid plain text response,
        so it contains the MOST RECENT substantive response. This allows the LLM
        to revise/improve its answer across confirmation rounds.

        Returns:
            The final response text.
        """
        # Save the held message BEFORE clearing the stack
        held = self._eot_confirmation_stack[-1] if self._eot_confirmation_stack else None
        stack_depth = len(self._eot_confirmation_stack)

        # Pop the LLM's confirmation response (assistant message) BEFORE
        # calling pop_all_confirmations(). The context structure is:
        #   ... → assistant(held) → user(eot_confirmation) → assistant(LLM response)
        # pop_all_confirmations expects user at msgs[-1], so we must remove
        # the LLM's assistant response first.
        msgs = self._context._messages
        if msgs and msgs[-1].get("role") == "assistant":
            msgs.pop()

        self.pop_all_confirmations()

        # --- Response selection: prefer last_substantive_response (most recent) ---
        # last_substantive_response is now updated on EVERY valid plain text
        # response, so it contains the MOST RECENT substantive response.
        # This allows the LLM to revise/improve its answer across confirmation rounds.
        substantive = self._agent.last_substantive_response
        held_text = held.get("text", "") if held else ""

        if substantive:
            final_text = substantive
            source = "last_substantive_response"
        elif held_text and not _looks_like_malformed_tool_call(held_text):
            final_text = held_text
            source = "held_message"
        else:
            final_text = ""
            source = "empty_fallback"

        # --- Audit: log confirmation acceptance ---
        self._audit_writer._emit(
            "EOT_CONFIRM_ACCEPTED",
            f"source={source} stack_depth={stack_depth} final_len={len(final_text)}"
        )
        from agent_console import status as _status
        _status(
            f"[EOT] Turn confirmed (source: {source}, stack: {stack_depth})"
        )

        # Append the final assistant message
        self._context.append_assistant(
            final_text,
            reasoning=held.get("reasoning") if held else None,
        )

        # Close turn
        self._context.close_turn(final_text)
        self._audit_writer.assistant(final_text)
        return final_text

    # ── Budget checking ──────────────────────────────────────────────────────

    def increment_and_check_budget(self) -> bool:
        """Increment the accidental EOT counter and check if budget is exhausted.

        Returns:
            True if the budget is exhausted, False otherwise.
        """
        self._accidental_eot_counter += 1
        return self._accidental_eot_counter > _ACCIDENTAL_EOT_BUDGET