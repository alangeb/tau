"""Context compression algorithms for LLM conversation management.

Eleven pipeline steps applied until target size is reached. Nine functions
implement these steps — `compress_tool_pruning` and `compress_redact_blocks`
each serve two steps via the `use_boundary` parameter.

1. compress_prune_images — replace image content blocks with text placeholders
2. compress_oversized_tool_redaction — redact single oversized tool results
3. compress_drop_reasoning — strip reasoning fields from assistant messages
4. compress_last_transaction — LLM summarization of completed turns
5. compress_tool_pruning — replace large tool outputs with placeholders (50% boundary)
6. compress_redact_blocks — strip intermediate messages from completed blocks (50% boundary)
7. compress_tool_pruning (use_boundary=False) — same as #5, scans entire context
8. compress_redact_blocks (use_boundary=False) — same as #6, scans entire context
9. compress_full_reset — full context rebuild (last resort)
10. compress_conversation_summary — deterministic conversation restructuring (fallback)
11. compress_blind_truncate — truncate summary from beginning (guaranteed fit)

ARCHITECTURE:

- Fixed 50% boundary: protects recent messages (current task state).
  Steps 2-6 operate within the boundary. Steps 7-8 ignore it.
- Right-to-left scanning: preserves KV cache prefix (step 4).
  Steps 5-8 scan left-to-right from index 0.
- Parameter consistency: same model/tools/params across compression calls.
- Compression prompt stability: prompts must not change between calls.

LOGGING:

- Console: One-liner per pipeline step via compression_step_summary().
- Audit: Per-action detail via audit_writer.compress_start/action/step_end().
- Errors/warnings: Continue via error() / warning() as before.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
import json


@dataclass
class CompressionStep:
    """Declarative registration for a compression pipeline step.

    Stores the *impl_fn* (the core algorithm) and optional *kwargs* to forward
    to the impl (e.g. ``use_boundary``).  The pipeline calls ``_compress_wrapper``
    directly — no intermediate wrapper function needed.
    """
    name: str
    impl_fn: Callable[..., tuple[list[dict], str]]
    kwargs: dict[str, Any] = field(default_factory=dict)

# Import directly from leaf modules to break the diamond circular-import:
# agent_context_compress → agent_console → agent_console.messages
# agent_context_compress → agent_llm → agent_console → agent_console.messages
# By importing error & compression_step_summary directly, agent_console is never
# pulled in at module level, so agent_console.messages always finishes loading
# before any path tries to re-import it.
from agent_console import (
    compression_step_summary,
    echo,
    error,
    verbose as _verbose,
)
from agent_llm_models import DEFAULT_MAX_CONTEXT_TOKENS, DEFAULT_MAX_OUTPUT_TOKENS, LLMCallConfig, LLMResponse
from agent_llm_invoke import _invoke_llm_with_retry
from agent_message_utils import is_synthetic_message
from agent_models import Colors

# --- Constants ---

MAX_ITERATIONS = 100
MIN_BLOCK_SIZE = 300
OVERSIZED_THRESHOLD = 0.20
PRUNE_THRESHOLD = 100
# Maximum size for individual tool results in conversation summary (bytes)
SUMMARY_TOOL_RESULT_MAX_BYTES = 4096

__all__ = [
    "compress_context",
]


def _invoke_llm_with_retry_compression(
    client,
    model_name: str,
    messages: list,
    tools: list,
    tool_choice: str | None,
    stream: bool,
    max_retries: int = 5,
    min_response_bytes: int = 10,
    extra_kwargs: dict | None = None,
    log_file: Path | None = None,
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> LLMResponse:
    """Thin wrapper around ``_invoke_llm_with_retry`` for compression calls."""
    config = LLMCallConfig(
        max_retries=max_retries,
        min_response_bytes=min_response_bytes,
        log_on_failure=True,
        log_file=log_file,
        extra_kwargs=extra_kwargs,
        max_context_tokens=max_context_tokens,
        max_output_tokens=max_output_tokens,
    )

    resp, _compressed = _invoke_llm_with_retry(
        client=client,
        model_name=model_name,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
        stream=stream,
        config=config,
    )
    # Compression callers don't need the compressed messages — they pass
    # temporary lists, not the agent's persistent context.

    if not resp.success:
        raise resp.error or RuntimeError("Compression LLM call failed")
    return resp


# --- Helpers ---


def _calculate_context_bytes(context: list[dict]) -> int:
    """Total byte size of serialized context messages."""
    return sum(len(json.dumps(m)) for m in context)


def compute_compression_target_bytes(
    current_bytes: int,
    compression_factor: float,
    last_known_tokens: int | None,
    max_context_tokens: int,
    max_output_tokens: int,
) -> int:
    """Return the byte target for compression.

    Uses the MINIMUM of:
    1. Byte-based target: current_bytes × (1 - compression_factor)
    2. Token-derived target: current_bytes × (1 - reduction_ratio)

    The token-derived target is computed from the token budget:
        target_tokens = max_context_tokens - max_output_tokens - compression_factor × max_context_tokens
        reduction_ratio = (last_known_tokens - target_tokens) / last_known_tokens

    The compression_factor (typically 0.3) serves dual purpose:
    - Byte target: aims for 30% byte reduction
    - Token budget: reserves 30% of context window as breathing room for new content

    Assumes linear byte-to-token scaling. If compression removes byte-heavy,
    token-cheap content first (ratio collapse), multiple compression rounds
    may be needed.
    """
    # --- Byte-based target ---
    byte_target = int(current_bytes * (1 - compression_factor))

    # --- Token-derived target ---
    token_target = byte_target  # default fallback

    if last_known_tokens is not None and last_known_tokens > 0:
        # Token budget: reserve breathing room (compression_factor × MCW) + output tokens
        breathing_room = int(compression_factor * max_context_tokens)
        target_tokens = max_context_tokens - max_output_tokens - breathing_room
        target_tokens = max(0, target_tokens)  # Guard against negative

        if last_known_tokens > target_tokens:
            # Need to reduce tokens
            reduction_ratio = (last_known_tokens - target_tokens) / last_known_tokens

            # Apply reduction ratio directly to bytes (linear assumption)
            token_byte_target = int(current_bytes * (1 - reduction_ratio))

            # Use the more aggressive (lower) target
            token_target = min(byte_target, token_byte_target)

    return token_target


def _compute_50_boundary(context: list[dict]) -> tuple[int, int]:
    """Return (boundary_50_bytes, boundary_idx) for the current context."""
    boundary_50_bytes = _calculate_context_bytes(context) // 2
    boundary_idx = _find_50_boundary(context, boundary_50_bytes)
    return boundary_50_bytes, boundary_idx


def _has_unresolved_tool_calls(block: list[dict]) -> bool:
    """True if any assistant tool_call in *block* lacks a matching tool result."""
    pending: set[str] = set()
    for msg in block:
        if msg.get("role") == "assistant":
            for tc in msg.get("tool_calls", []):
                if isinstance(tc, dict) and tc.get("id"):
                    pending.add(tc["id"])
        elif msg.get("role") == "tool":
            tid = msg.get("tool_call_id")
            if tid:
                pending.discard(tid)
    return bool(pending)


def _has_orphaned_tool_results(block: list[dict]) -> bool:
    """True if any tool result references a tool_call_id from outside *block*."""
    ids_in_block = {
        tc["id"]
        for msg in block
        if msg.get("role") == "assistant"
        for tc in msg.get("tool_calls", [])
        if isinstance(tc, dict) and tc.get("id")
    }
    return any(
        msg.get("tool_call_id") and msg.get("tool_call_id") not in ids_in_block
        for msg in block
        if msg.get("role") == "tool"
    )


def _find_50_boundary(context: list[dict], boundary_bytes: int) -> int:
    """Return the index where cumulative bytes first exceed *boundary_bytes*."""
    cumulative = 0
    for i, msg in enumerate(context):
        cumulative += len(json.dumps(msg))
        if cumulative > boundary_bytes:
            return i
    return len(context)


def _find_user_assistant_block(context: list[dict], pointer: int) -> tuple[int | None, int | None, int]:
    """Find a completed turn (user...assistant) scanning right-to-left from *pointer*.

    Returns (user_idx, assistant_idx, block_end) or (None, None, pointer).
    """
    assistant_idx = None
    for i in range(pointer - 1, -1, -1):
        if context[i].get("role") == "assistant" and not context[i].get("tool_calls"):
            assistant_idx = i
            break
    if assistant_idx is None:
        return None, None, pointer

    user_idx = None
    for i in range(assistant_idx - 1, -1, -1):
        if context[i].get("role") == "user" and not is_synthetic_message(context[i]):
            user_idx = i
            break
    if user_idx is None:
        return None, None, pointer

    next_user_idx = next(
        (i for i in range(assistant_idx + 1, len(context))
         if context[i].get("role") == "user" and not is_synthetic_message(context[i])),
        None,
    )
    block_end = next_user_idx if next_user_idx else len(context)
    return user_idx, assistant_idx, block_end


def _extract_text_from_content(content) -> str:
    """Extract text from content (str or multimodal list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [p.get("text", "") for p in content if p.get("type") == "text"]
        return " ".join(parts)
    return ""


# --- Metadata helper ---


def _make_metadata(
    step_name: str,
    bytes_before: int,
    bytes_after: int,
    msgs_before: int,
    msgs_after: int,
    actions: list[str],
    status: str,
) -> dict:
    return {
        "step_name": step_name,
        "bytes_before": bytes_before,
        "bytes_after": bytes_after,
        "msgs_before": msgs_before,
        "msgs_after": msgs_after,
        "actions": actions,
        "status": status,
    }


def _compress_wrapper(
    step_name: str,
    impl_fn: Callable[..., tuple[list[dict], str]],
    context: list[dict],
    target_size_bytes: int,
    verbose: bool = False,
    audit_writer: Any = None,
    **impl_kwargs,
) -> tuple[list[dict], dict]:
    """Handle common boilerplate for compression algorithms.

    The implementation function (impl_fn) should accept:
        (current_context, target_size_bytes, verbose, audit_writer, actions, step_name, **kwargs)
    And return:
        (context, status)

    The wrapper handles:
        - original_size / msgs_before calculation
        - final_size / msgs_after calculation
        - audit logging (compress_start, compress_step_end)
        - metadata generation
        - system message preservation

    *impl_kwargs* are forwarded to *impl_fn* to avoid closure boilerplate.
    """
    original_size = _calculate_context_bytes(context)
    msgs_before = len(context)
    current_context = list(context)
    actions: list[str] = []

    # Preserve system message for restoration if compression loses it
    system_msg = (
        context[0] if context and context[0].get("role") == "system" else None
    )

    new_context, status = impl_fn(
        current_context, target_size_bytes, verbose, audit_writer, actions, step_name, **impl_kwargs
    )

    # Ensure system message is preserved after compression
    if system_msg and (not new_context or new_context[0].get("role") != "system"):
        if verbose:
            _verbose(f"  :: {step_name}: restoring lost system message")
        new_context.insert(0, system_msg)

    final_size = _calculate_context_bytes(new_context)
    msgs_after = len(new_context)

    if audit_writer is not None:
        audit_writer.compress_start(step_name, original_size, msgs_before)
        audit_writer.compress_step_end(step_name, final_size, msgs_after, status)

    metadata = _make_metadata(step_name, original_size, final_size, msgs_before, msgs_after, actions, status)
    return new_context, metadata


# --- Algorithm 0: Image Pruning (most aggressive) ---


def _compress_prune_images_impl(
    current_context: list[dict],
    target_size_bytes: int,
    verbose: bool,
    audit_writer: Any,
    actions: list[str],
    step_name: str,
    **kwargs,
) -> tuple[list[dict], str]:
    """Core image pruning algorithm — replace all but last image per user message."""
    boundary_50_bytes, boundary_idx = _compute_50_boundary(current_context)

    for i in range(boundary_idx, -1, -1):
        msg = current_context[i]
        if msg.get("role") != "user":
            continue

        content = msg.get("content")
        if not isinstance(content, list):
            continue

        image_indices = [
            j for j, p in enumerate(content) if p.get("type") == "image_url"
        ]
        if len(image_indices) <= 1:
            continue  # Only one image, keep it

        # Keep the LAST image, replace all others
        indices_to_remove = set(image_indices[:-1])

        new_content = []
        for j, part in enumerate(content):
            if j in indices_to_remove:
                new_content.append({
                    "type": "text",
                    "text": "[IMAGE: removed by compression]",
                })
            else:
                new_content.append(part)

        old_bytes = len(json.dumps(msg))
        current_context[i] = {**msg, "content": new_content}
        new_bytes = len(json.dumps(current_context[i]))
        savings = old_bytes - new_bytes

        action_desc = f"pruned {len(indices_to_remove)} image(s) from user msg {i}: {old_bytes}B -> {new_bytes}B"
        actions.append(action_desc)

        if audit_writer is not None:
            audit_writer.compress_action(step_name, "prune_images", action_desc)

        if verbose:
            _verbose(f"  :: IMAGE_PRUNED msg #{i}: SAVED {savings:,} bytes")

        if _calculate_context_bytes(current_context) <= target_size_bytes:
            break

    final_size = _calculate_context_bytes(current_context)
    status = "ACHIEVED" if final_size <= target_size_bytes else "PARTIAL"
    return current_context, status


def compress_prune_images(
    context: list[dict],
    client,
    model_name: str,
    target_size_bytes: int,
    verbose: bool = False,
    audit_writer: Any = None,
    **kwargs,
) -> tuple[list[dict], dict]:
    """Replace image content blocks with text placeholders.

    Strategy: Scan right-to-left within 50% boundary. For each user message
    with image blocks, replace all but the last image_url block with a text
    placeholder.  This is the most aggressive step — images dominate context size.
    """
    return _compress_wrapper("PRUNE_IMAGES", _compress_prune_images_impl, context, target_size_bytes, verbose, audit_writer, **kwargs)


# --- Algorithm 1: Oversized Tool Redaction ---


def _compress_oversized_tool_redaction_impl(
    current_context: list[dict],
    target_size_bytes: int,
    verbose: bool,
    audit_writer: Any,
    actions: list[str],
    step_name: str,
    **kwargs,
) -> tuple[list[dict], str]:
    """Core oversized tool redaction — redact tool results >20% of context."""
    original_size = _calculate_context_bytes(current_context)
    boundary_50_bytes, boundary_idx = _compute_50_boundary(current_context)
    limit = min(boundary_idx, len(current_context) - 1)

    i = 0
    while i <= limit:
        msg = current_context[i]
        if msg.get("role") == "tool":
            msg_bytes = len(str(msg.get("content", "")))
            rest_bytes = _calculate_context_bytes(current_context) - msg_bytes
            if rest_bytes > 0 and msg_bytes / rest_bytes > OVERSIZED_THRESHOLD:
                tool_name = msg.get("name", "unknown")
                pct = msg_bytes / rest_bytes * 100
                redacted_content = (
                    f"[REDACTED: {tool_name} result was {msg_bytes} bytes "
                    f"({pct:.1f}% of context). Content removed by compression.]"
                )
                old_bytes = msg_bytes
                current_context[i] = {
                    "role": "tool",
                    "content": redacted_content,
                    "tool_call_id": msg.get("tool_call_id", ""),
                    "name": msg.get("name", ""),
                }
                new_bytes = len(str(redacted_content))
                savings = old_bytes - new_bytes
                action_desc = f"redacted tool '{tool_name}' at msg {i}: {old_bytes}B → {new_bytes}B"
                actions.append(action_desc)
                if audit_writer is not None:
                    audit_writer.compress_action(step_name, "redact_tool", action_desc)
                if verbose:
                    _verbose(f"  :: REDACTED tool@{i}: {tool_name} {old_bytes:,} -> {new_bytes:,} bytes (saved {savings:,})")
                boundary_50_bytes = original_size // 2
                boundary_idx = _find_50_boundary(current_context, boundary_50_bytes)
        i += 1

    final_size = _calculate_context_bytes(current_context)
    status = "NO_REDUCTION" if final_size == original_size else "REDUCED"
    return current_context, status


def compress_oversized_tool_redaction(
    context: list[dict],
    client,
    model_name: str,
    target_size_bytes: int,
    verbose: bool = False,
    audit_writer: Any = None,
    **kwargs,
) -> tuple[list[dict], dict]:
    """Redact tool results >20% of remaining context bytes (within 50% boundary).

    Returns (context, metadata).
    """
    return _compress_wrapper("OVERSIZED_TOOL_REDACTION", _compress_oversized_tool_redaction_impl, context, target_size_bytes, verbose, audit_writer, **kwargs)


# --- Algorithm 1b: Drop Reasoning ---


def _compress_drop_reasoning_impl(
    current_context: list[dict],
    target_size_bytes: int,
    verbose: bool,
    audit_writer: Any,
    actions: list[str],
    step_name: str,
    **kwargs,
) -> tuple[list[dict], str]:
    """Core reasoning drop — strip reasoning fields from assistant messages."""
    original_size = _calculate_context_bytes(current_context)
    boundary_50_bytes, boundary_idx = _compute_50_boundary(current_context)

    for i in range(min(boundary_idx, len(current_context))):
        msg = current_context[i]
        if msg.get("role") == "assistant" and "reasoning" in msg:
            reasoning_text = msg["reasoning"]
            reasoning_bytes = len(str(reasoning_text))
            del current_context[i]["reasoning"]
            action_desc = f"dropped reasoning at msg {i}: {reasoning_bytes}B"
            actions.append(action_desc)
            if audit_writer is not None:
                audit_writer.compress_action(step_name, "drop_reasoning", action_desc)
            if verbose:
                _verbose(f"  :: DROPPED reasoning@{i}: {reasoning_bytes:,} bytes")

    final_size = _calculate_context_bytes(current_context)
    status = "NO_REDUCTION" if final_size == original_size else "REDUCED"
    return current_context, status


def compress_drop_reasoning(
    context: list[dict],
    client,
    model_name: str,
    target_size_bytes: int,
    verbose: bool = False,
    audit_writer: Any = None,
    **kwargs,
) -> tuple[list[dict], dict]:
    """Drop ``reasoning`` fields from assistant messages within the 50% boundary.

    Keeps all messages intact — only strips the reasoning content.
    Returns (context, metadata).
    """
    return _compress_wrapper("DROP_REASONING", _compress_drop_reasoning_impl, context, target_size_bytes, verbose, audit_writer, **kwargs)


# --- Algorithm 2: Last Transaction Compression ---


COMPRESSION_PROMPT = """You are an expert conversation summarizer. Your task is to compress a completed user-assistant interaction while preserving ALL valuable information.

## WHAT TO PRESERVE (CRITICAL):

### 1. USER'S GOAL/INTENT
- What was the user trying to accomplish?

### 2. ASSISTANT'S ACTION PLAN
- What approach did the assistant decide on?
- What tools were selected and why?

### 3. TOOL EXECUTION DETAILS
- Which tools were called with what arguments?
- What were the actual tool results/output?

### 4. KEY FINDINGS & INSIGHTS
- What important information was discovered?

### 5. FILE OPERATIONS (CRITICAL)
- Which files were read, written, created, or modified?
- What were the file paths and key contents?

### 6. COMMANDS RUN & OUTPUTS
- What shell commands were executed?
- What were the key outputs?

### 7. TECHNICAL DECISIONS
- What architectural or implementation decisions were made?

### 8. OPEN QUESTIONS & NEXT STEPS
- What remains unresolved?
- What should the next turn focus on?

### 9. MODEL REASONING / THINKING (if present)
- Some messages may include a "reasoning" field containing the model's
  chain-of-thought.
- If present, either:
  a) Preserve key reasoning steps in your summary, OR
  b) Note that reasoning was present without including verbatim text
- Do NOT discard reasoning content — it contains important decision process
  that may be needed for subsequent tool calls or continuation

## SUMMARY STRUCTURE (markdown format):

## GOAL
[User's objective in 1-2 sentences]

## ACTIONS TAKEN
[What the assistant did, step by step]

## TOOL CALLS & RESULTS
- TOOL_NAME(args) -> [key result or error]

## KEY FINDINGS
[All important discoveries]

## DECISIONS MADE
[Technical choices and their rationale]

## FILES AFFECTED
[File paths and what happened to each]

## COMMANDS EXECUTED
[Commands run with their significance]

## CURRENT STATE
[Where we are now, what's completed, what remains]

## NEXT STEPS
[What should happen next]

## ESSENTIAL REFERENCES
[Any specific code sections, line numbers, concepts]

## MODEL REASONING (if present in original)
[Key reasoning steps or "Model was reasoning internally (content compressed)" if reasoning was present but not critical]

REPLY WITH SUMMARY ONLY - no tool calls, no extra text. DO NOT USE TOOLS! ONLY REPLY FROM MEMORY!"""


def _compress_last_transaction_impl(
    current_context: list[dict],
    target_size_bytes: int,
    verbose: bool,
    audit_writer: Any,
    actions: list[str],
    step_name: str,
    **kwargs,
) -> tuple[list[dict], str]:
    """Core last transaction compression — LLM summarization of completed turns."""
    client = kwargs.get("client")
    model_name = kwargs.get("model_name")
    tools = kwargs.get("tools")
    extra_kwargs = kwargs.get("extra_kwargs")
    log_file = kwargs.get("log_file")
    max_context_tokens = kwargs.get("max_context_tokens", DEFAULT_MAX_CONTEXT_TOKENS)
    max_output_tokens = kwargs.get("max_output_tokens", DEFAULT_MAX_OUTPUT_TOKENS)

    original_size = _calculate_context_bytes(current_context)
    blocks_compressed = 0
    blocks_skipped = 0

    boundary_50_bytes, boundary_msg_idx = _compute_50_boundary(current_context)

    if verbose:
        echo(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
        echo(f"{Colors.CYAN}>>> LAST_TRANSACTION START >>>{Colors.RESET}")
        echo(
            f"{Colors.CYAN}  target={target_size_bytes:,} bytes, current={_calculate_context_bytes(current_context):,} bytes, 50%={original_size // 2:,} bytes{Colors.RESET}"
        )
        echo(
            f"{Colors.CYAN}  50% boundary at msg index {boundary_msg_idx} (of {len(current_context)-1}){Colors.RESET}"
        )
        echo(f"{Colors.CYAN}{'='*70}{Colors.RESET}")

    pointer = len(current_context)

    iteration = 0
    while _calculate_context_bytes(current_context) > target_size_bytes and iteration < MAX_ITERATIONS:
        iteration += 1

        user_idx, assistant_idx, block_end = _find_user_assistant_block(current_context, pointer)

        if user_idx is None:
            if verbose:
                _verbose(f"  :: Iteration {iteration}: no completed block found before pointer={pointer} - STOP")
            break

        if boundary_msg_idx is not None and user_idx >= boundary_msg_idx:
            blocks_skipped += 1
            if verbose:
                _verbose(
                    f"  :: Iteration {iteration}: user@{user_idx} at or right of 50% boundary@{boundary_msg_idx} - SKIP, scanning left"
                )
            pointer = user_idx
            continue

        block = current_context[user_idx:block_end]
        assistant_tool_part = current_context[user_idx + 1:block_end]
        block_bytes = _calculate_context_bytes(block)
        user_msg = current_context[user_idx]

        if verbose:
            _verbose(f"  :: Iteration {iteration}: block [{user_idx}:{block_end}] = {block_bytes} bytes ({len(block)} msgs)")

        skip_reason = None
        if not any(m.get("role") == "tool" for m in assistant_tool_part):
            skip_reason = "no tool calls in block"
        elif _has_unresolved_tool_calls(block):
            skip_reason = "unresolved tool calls inside block"
        elif _has_orphaned_tool_results(block):
            skip_reason = "orphaned tool results referencing assistants outside block"
        elif block_bytes < MIN_BLOCK_SIZE:
            skip_reason = f"block too small ({block_bytes} bytes < {MIN_BLOCK_SIZE})"

        if skip_reason:
            blocks_skipped += 1
            if verbose:
                _verbose(f"  :: SKIP (reason: {skip_reason}) - keeping block as-is, moving left")
            pointer = user_idx
            continue

        if verbose:
            _verbose(
                f"  :: Calling LLM to compress {len(assistant_tool_part)} messages ({_calculate_context_bytes(assistant_tool_part):,} bytes)..."
            )

        context_for_summary = [
            {"role": "system", "content": COMPRESSION_PROMPT},
            {
                "role": "user",
                "content": "Compress the following conversation:\n\n"
                + "\n".join(
                    f"[{m.get('role', 'unknown').upper()}]\n"
                    f"content: {_extract_text_from_content(m.get('content', ''))}\n"
                    f"reasoning: {m.get('reasoning', '')}"
                    for m in assistant_tool_part
                ),
            },
        ]

        try:
            resp = _invoke_llm_with_retry_compression(
                client, model_name, context_for_summary, tools, "auto",
                stream=False, extra_kwargs=extra_kwargs, log_file=log_file,
                max_context_tokens=max_context_tokens,
                max_output_tokens=max_output_tokens,
            )
            response = resp.raw
            response_text = resp.text

            if not response or not response.choices or not response_text or not response_text.strip():
                blocks_skipped += 1
                if verbose:
                    _verbose("  :: LLM returned empty/invalid - keeping block as-is, moving left")
                pointer = user_idx
                continue

            summary = response_text.strip()
            new_block = [
                user_msg,
                {"role": "assistant", "content": summary},
            ]
            new_block_bytes = _calculate_context_bytes(new_block)

            if new_block_bytes >= block_bytes:
                blocks_skipped += 1
                if verbose:
                    _verbose(
                        f"  :: Compression not beneficial: {block_bytes:,} -> {new_block_bytes:,} bytes - keeping block as-is, moving left"
                    )
                pointer = user_idx
                continue

            savings = block_bytes - new_block_bytes
            blocks_compressed += 1
            action_desc = f"compressed block [{user_idx}:{block_end}]: {block_bytes}B → {new_block_bytes}B (saved {savings}B)"
            actions.append(action_desc)
            if audit_writer is not None:
                audit_writer.compress_action(step_name, "compress_block", action_desc)
            if verbose:
                _verbose(
                    f"  :: COMPRESSED [{user_idx}:{block_end}]: {block_bytes:,} -> {new_block_bytes:,} bytes (saved {savings:,})"
                )
            current_context = (
                current_context[:user_idx] + new_block + current_context[block_end:]
            )

        except Exception as e:
            blocks_skipped += 1
            if verbose:
                _verbose(f"  :: LLM error: {e} - keeping block as-is, moving left")

        pointer = user_idx

    final_size = _calculate_context_bytes(current_context)
    status = "ACHIEVED" if final_size <= target_size_bytes else "NO_MORE_BLOCKS"

    if verbose:
        compression_end_msg = f"[COMPRESS] LAST_TRANSACTION: {len(current_context)} msgs, {final_size:,} bytes -> target {target_size_bytes / original_size * 100 if original_size > 0 else 0:.0f}% ({target_size_bytes:,} bytes) [{status}]"
        _verbose(compression_end_msg)

    return current_context, status


def compress_last_transaction(
    context: list[dict],
    client,
    model_name: str,
    target_size_bytes: int,
    tools: list | None = None,
    extra_kwargs: dict[str, Any] | None = None,
    verbose: bool = False,
    log_file: Path | None = None,
    audit_writer: Any = None,
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> tuple[list[dict], dict]:
    """Rewrite completed turns (right-to-left, within first 50%) via LLM summary.

    Returns (context, metadata).
    """
    return _compress_wrapper(
        "LAST_TRANSACTION", _compress_last_transaction_impl, context, target_size_bytes, verbose, audit_writer,
        client=client, model_name=model_name, tools=tools, extra_kwargs=extra_kwargs,
        log_file=log_file, max_context_tokens=max_context_tokens, max_output_tokens=max_output_tokens,
    )


# --- Algorithm 2b/6: Tool Pruning (unified with boundary parameter) ---


def _compress_tool_pruning_impl(
    current_context: list[dict],
    target_size_bytes: int,
    verbose: bool,
    audit_writer: Any,
    actions: list[str],
    step_name: str,
    use_boundary: bool,
    **kwargs,
) -> tuple[list[dict], str]:
    """Core tool pruning logic.

    Args:
        use_boundary: If True, prune only within 50% boundary. If False, prune entire context.
    """
    if use_boundary:
        _, boundary_idx = _compute_50_boundary(current_context)

    iteration = 0
    while _calculate_context_bytes(current_context) > target_size_bytes:
        iteration += 1
        if iteration > MAX_ITERATIONS:
            if verbose:
                error("  :: ITERATION LIMIT REACHED (100), STOPPING")
            break

        if verbose:
            echo(f"{Colors.YELLOW}{'-'*70}{Colors.RESET}")
            echo(
                f"  :: ITERATION #{iteration} START: current_size={_calculate_context_bytes(current_context):,} bytes, target={target_size_bytes:,} bytes"
            )

        # Recompute scan limit each iteration (context shrinks as tools are pruned)
        if use_boundary:
            _, boundary_idx = _compute_50_boundary(current_context)
            scan_limit = boundary_idx + 1
        else:
            scan_limit = len(current_context)

        for i in range(scan_limit):
            msg = current_context[i]
            if msg.get("role") == "tool":
                tool_content = msg.get("content", "")
                tool_bytes = len(str(tool_content))

                if tool_bytes > PRUNE_THRESHOLD:
                    tool_name = msg.get("name", "unknown")
                    if verbose:
                        _verbose(f"  :: Found prunable tool at msg #{i}, content_size={tool_bytes:,} bytes")

                    current_context[i] = {
                        "role": "tool",
                        "content": "COMPRESSION: CALL RESULT NO LONGER AVAILABLE",
                        "tool_call_id": current_context[i].get("tool_call_id", ""),
                        "name": current_context[i].get("name", ""),
                    }

                    new_bytes = len("COMPRESSION: CALL RESULT NO LONGER AVAILABLE")
                    savings = tool_bytes - new_bytes
                    action_desc = f"pruned tool '{tool_name}' at msg {i}: {tool_bytes}B → {new_bytes}B"
                    actions.append(action_desc)
                    if audit_writer is not None:
                        audit_writer.compress_action(step_name, "prune_tool", action_desc)

                    if verbose:
                        _verbose(f"  :: TOOL_PRUNED msg #{i}: SAVED {savings:,} bytes")

                    break
        else:
            # No prunable tool found in this iteration
            if verbose:
                boundary_msg = "within boundary" if use_boundary else "in context"
                _verbose(f"  :: No more tools with content > 100 bytes found {boundary_msg}")
            break

    final_size = _calculate_context_bytes(current_context)
    status = "ACHIEVED" if final_size <= target_size_bytes else "NO_MORE_TOOLS"
    return current_context, status


def compress_tool_pruning(
    context: list[dict],
    client,
    model_name: str,
    target_size_bytes: int,
    verbose: bool = False,
    audit_writer: Any = None,
    use_boundary: bool = True,
    **kwargs,
) -> tuple[list[dict], dict]:
    """Replace tool outputs >100 bytes with a placeholder.

    Args:
        use_boundary: If True, prune only within 50% boundary. If False, prune entire context.

    Returns (context, metadata).
    """
    step_name = "TOOL_PRUNING" if use_boundary else "TOOL_PRUNING_FULL"
    return _compress_wrapper(
        step_name, _compress_tool_pruning_impl,
        context, target_size_bytes, verbose, audit_writer,
        use_boundary=use_boundary,
    )


# --- Algorithm 3/7: Redact Blocks (unified with boundary parameter) ---


def _compress_redact_blocks_impl(
    current_context: list[dict],
    target_size_bytes: int,
    verbose: bool,
    audit_writer: Any,
    actions: list[str],
    step_name: str,
    use_boundary: bool,
    **kwargs,
) -> tuple[list[dict], str]:
    """Core block redaction logic.

    Args:
        use_boundary: If True, redact only within 50% boundary. If False, redact entire context.
    """
    iteration = 0
    while _calculate_context_bytes(current_context) > target_size_bytes:
        iteration += 1
        if iteration > MAX_ITERATIONS:
            if verbose:
                error("  :: ITERATION LIMIT REACHED (100), STOPPING")
            break

        if verbose:
            echo(f"{Colors.YELLOW}{'-'*70}{Colors.RESET}")
            echo(
                f"  :: ITERATION #{iteration} START: current_size={_calculate_context_bytes(current_context):,} bytes, target={target_size_bytes:,} bytes"
            )

        # Recompute scan limit each iteration (context shrinks as blocks are redacted)
        if use_boundary:
            _, boundary_idx = _compute_50_boundary(current_context)
            scan_limit = boundary_idx
        else:
            scan_limit = len(current_context)

        found_block = False
        i = 0
        while i <= scan_limit:
            # Safety: break if i exceeds current context length (can happen after redaction)
            if i >= len(current_context):
                break
            if current_context[i].get("role") == "user" and not is_synthetic_message(current_context[i]):
                user_idx = i
                assistant_idx = None

                for j in range(i + 1, scan_limit):
                    if current_context[j].get("role") == "user" and not is_synthetic_message(current_context[j]):
                        break
                    if current_context[j].get("role") == "assistant" and not current_context[j].get("tool_calls"):
                        assistant_idx = j
                        break

                if assistant_idx is not None:
                    block = current_context[user_idx:assistant_idx + 1]
                    block_bytes = _calculate_context_bytes(block)

                    if block_bytes < MIN_BLOCK_SIZE:
                        if verbose:
                            _verbose(f"     ✗ Block too small (< {MIN_BLOCK_SIZE} bytes) - SKIP")
                        i = assistant_idx + 1
                        continue

                    if _has_unresolved_tool_calls(block):
                        if verbose:
                            _verbose("     ✗ Block contains unresolved tool calls - SKIP")
                        i = assistant_idx + 1
                        continue

                    if _has_orphaned_tool_results(block):
                        if verbose:
                            _verbose("     ✗ Block contains orphaned tool results - SKIP")
                        i = assistant_idx + 1
                        continue

                    removed_count = len(block) - 2
                    new_block = [
                        current_context[user_idx],
                        current_context[assistant_idx],
                    ]
                    new_bytes = _calculate_context_bytes(new_block)
                    savings = block_bytes - new_bytes
                    action_desc = f"redacted block [{user_idx}:{assistant_idx}]: {block_bytes}B → {new_bytes}B (removed {removed_count} intermediates)"
                    actions.append(action_desc)
                    if audit_writer is not None:
                        audit_writer.compress_action(step_name, "redact_block", action_desc)

                    if verbose:
                        _verbose(f"  :: BLOCK #{user_idx}-{assistant_idx} REDACTED: SAVED {savings:,} bytes (removed {removed_count} intermediates)")

                    current_context = (
                        current_context[:user_idx]
                        + new_block
                        + current_context[assistant_idx + 1:]
                    )
                    found_block = True
                    break

            i += 1

        if not found_block:
            if verbose:
                boundary_msg = "within boundary" if use_boundary else "in context"
                _verbose(f"  :: No more completed blocks to redact {boundary_msg}")
            break

    final_size = _calculate_context_bytes(current_context)
    status = "ACHIEVED" if final_size <= target_size_bytes else "NO_MORE_BLOCKS"
    return current_context, status


def compress_redact_blocks(
    context: list[dict],
    client,
    model_name: str,
    target_size_bytes: int,
    verbose: bool = False,
    audit_writer: Any = None,
    use_boundary: bool = True,
    **kwargs,
) -> tuple[list[dict], dict]:
    """Strip intermediate messages from completed blocks, keeping only USER + ASSISTANT.

    Args:
        use_boundary: If True, redact only within 50% boundary. If False, redact entire context.

    Returns (context, metadata).
    """
    step_name = "REDACT_BLOCKS" if use_boundary else "REDACT_BLOCKS_FULL"
    return _compress_wrapper(
        step_name, _compress_redact_blocks_impl,
        context, target_size_bytes, verbose, audit_writer,
        use_boundary=use_boundary,
    )


# --- Algorithm 4: Full Reset (Last Resort) ---


SUMMARY_PROMPT = """You are an expert conversation summarizer. Summarize everything that has been accomplished so far in this conversation.

Focus on:

- Key accomplishments and results

- Files modified and their contents

- Commands executed and their outputs

- Decisions made

- Current state of the work

Be comprehensive but concise. Include all critical information that would be needed to continue this work."""


PLAN_PROMPT = """Based on the conversation history, what are the next steps needed to complete the task?
Provide a clear plan with concrete actions."""


def _compress_full_reset_impl(
    current_context: list[dict],
    target_size_bytes: int,
    verbose: bool,
    audit_writer: Any,
    actions: list[str],
    step_name: str,
    **kwargs,
) -> tuple[list[dict], str]:
    """Core full reset — LLM generates summary + plan, replaces entire context."""
    client = kwargs.get("client")
    model_name = kwargs.get("model_name")
    tools = kwargs.get("tools")
    extra_kwargs = kwargs.get("extra_kwargs")
    log_file = kwargs.get("log_file")
    max_context_tokens = kwargs.get("max_context_tokens", DEFAULT_MAX_CONTEXT_TOKENS)
    max_output_tokens = kwargs.get("max_output_tokens", DEFAULT_MAX_OUTPUT_TOKENS)

    original_size = _calculate_context_bytes(current_context)

    system_msg = current_context[0] if current_context and current_context[0].get("role") == "system" else None

    # Find the last real (non-synthetic) user message — the most recent turn's request
    last_real_user_idx = None
    for i in range(len(current_context) - 1, -1, -1):
        if current_context[i].get("role") == "user" and not is_synthetic_message(current_context[i]):
            last_real_user_idx = i
            break

    if last_real_user_idx is None:
        if verbose:
            error("  :: No real user prompt found! Returning unchanged context.")
        return current_context, "FAILED_NO_USER"

    last_real_user_content = _extract_text_from_content(current_context[last_real_user_idx].get("content", ""))

    # LLM Request 1: summary — include everything up to and including the last real user message
    context_for_summary = (
        [{"role": "system", "content": SUMMARY_PROMPT},
         {"role": "user", "content": "Summarize everything you have done so far:"}]
        + current_context[1:last_real_user_idx + 1]
    )

    try:
        resp = _invoke_llm_with_retry_compression(
            client, model_name, context_for_summary, tools, "auto",
            stream=False, extra_kwargs=extra_kwargs, log_file=log_file,
            max_context_tokens=max_context_tokens,
            max_output_tokens=max_output_tokens,
        )
        summary = resp.text.strip() if resp.text else ""
        if verbose:
            _verbose(f"  :: LLM SUMMARY received ({len(summary):,} bytes)")
    except Exception as e:
        if verbose:
            error(f"  :: LLM SUMMARY FAILED: {e}")
        summary = ""

    # LLM Request 2: next steps plan
    context_for_plan = [
        {"role": "system", "content": PLAN_PROMPT},
        {
            "role": "user",
            "content": f"Current state summary:\n\n{summary}\n\nTell me about next steps to finish.",
        },
    ]

    try:
        resp = _invoke_llm_with_retry_compression(
            client, model_name, context_for_plan, tools, "auto",
            stream=False, extra_kwargs=extra_kwargs, log_file=log_file,
            max_context_tokens=max_context_tokens,
            max_output_tokens=max_output_tokens,
        )
        plan = resp.text.strip() if resp.text else ""
        if verbose:
            _verbose(f"  :: LLM NEXT STEPS received ({len(plan):,} bytes)")
    except Exception as e:
        if verbose:
            error(f"  :: LLM NEXT STEPS FAILED: {e}")
        plan = ""

    new_content = f"""# COMPREHENSION SUMMARY

{summary}

# NEXT STEPS & PLAN

{plan}

# CURRENT USER REQUEST

{last_real_user_content}"""

    if not summary and not plan:
        if verbose:
            error("  :: FULL_RESET FAILED - Both summary and plan empty. Returning unchanged context.")
        return current_context, "FAILED_EMPTY"

    new_context = []
    if system_msg:
        new_context.append(system_msg)
    new_context.append({"role": "user", "content": new_content})

    new_bytes = _calculate_context_bytes(new_context)
    msgs_after = len(new_context)
    action_desc = f"full reset: {len(current_context)} msgs ({original_size}B) → {msgs_after} msgs ({new_bytes}B)"
    actions.append(action_desc)

    if verbose:
        _verbose(f"  :: NEW CONTEXT: {len(new_context)} msgs, {new_bytes:,} bytes (from {len(current_context)} msgs)")

    return new_context, "RESET"


def compress_full_reset(
    context: list[dict],
    client,
    model_name: str,
    target_size_bytes: int,
    tools: list | None = None,
    extra_kwargs: dict[str, Any] | None = None,
    verbose: bool = False,
    log_file: Path | None = None,
    audit_writer: Any = None,
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> tuple[list[dict], dict]:
    """Full context rebuild: LLM generates summary + plan, replaces entire context.

    Returns (context, metadata).
    """
    return _compress_wrapper(
        "FULL_RESET", _compress_full_reset_impl, context, target_size_bytes, verbose, audit_writer,
        client=client, model_name=model_name, tools=tools, extra_kwargs=extra_kwargs,
        log_file=log_file, max_context_tokens=max_context_tokens, max_output_tokens=max_output_tokens,
    )


# --- Orchestrator ---


def _format_success(
    name: str,
    size: int,
    original_size: int,
    compression_factor: float,
    msg_count: int,
    algorithms_used: list[str],
    verbose: bool,
) -> tuple[str, dict]:
    """Build success summary string and metadata dict."""
    summary = f"✓ COMPRESSION ACHIEVED by {name} ({size:,} bytes)"
    if verbose:
        echo(f"\n{Colors.GREEN}{'='*70}{Colors.RESET}")
        echo(f"{Colors.GREEN}  COMPRESSION COMPLETE - EARLY SUCCESS!{Colors.RESET}")
        echo(f"{Colors.GREEN}{'='*70}{Colors.RESET}\n")
        echo(
            f"{Colors.GREEN}    Original: {original_size:,} bytes -> {size:,} bytes{Colors.RESET}"
        )
        echo(
            f"{Colors.GREEN}    Reduction: {(1 - size / original_size) * 100 if original_size > 0 else 0:.1f}% (target was {compression_factor*100:.0f}%) {Colors.RESET}"
        )
        echo(
            f"{Colors.GREEN}    Algorithms used: {' + '.join(algorithms_used)}{Colors.RESET}"
        )
        echo(
            f"{Colors.GREEN}    Final context: {size:,} bytes, {msg_count} messages{Colors.RESET}\n"
        )
    metadata = {
        "bytes_before": original_size,
        "bytes_after": size,
        "algorithms_used": algorithms_used,
    }
    return summary, metadata

def _build_action_summary(actions: list[str]) -> str:
    """Build a concise action summary string from the actions list."""
    if not actions:
        return "no changes"
    if len(actions) <= 3:
        return "; ".join(actions)
    return f"{actions[0]}; {actions[1]} ... ({len(actions)} total)"


# --- Algorithm 9: Conversation Summary (deterministic, no LLM) ---


def _extract_synthetic_category(msg: dict) -> str:
    """Extract category from synthetic message prefix.

    Handles both formats:
    - Legacy: [SYSTEM-SYNTHETIC: CATEGORY] content
    - New: [U:TYPE | N:stack] content (extracts TYPE)
    """
    content = msg.get("content", "")
    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text", "")
                break

    # New format: [U:TYPE | N:stack]
    if text.startswith("[U:"):
        end = text.find("|", 3)
        if end > 0:
            return text[3:end].strip()
    # Legacy format: [SYSTEM-SYNTHETIC: CATEGORY]
    prefix = "[SYSTEM-SYNTHETIC: "
    if text.startswith(prefix):
        end = text.find("]", len(prefix))
        if end > 0:
            return text[len(prefix):end]
    return "unknown"


def _get_tool_calls_for_assistant(msg: dict) -> list[dict]:
    """Extract tool_calls from an assistant message."""
    return msg.get("tool_calls", [])


def _is_within_turn(context: list[dict]) -> bool:
    """Check if the conversation is within a turn (has pending tool calls or awaiting response)."""
    if not context:
        return False
    last = context[-1]
    # Tool result at end = awaiting assistant response
    if last.get("role") == "tool":
        return True
    # Assistant with pending tool calls
    if last.get("role") == "assistant":
        tool_calls = last.get("tool_calls", [])
        if tool_calls:
            # Check if any tool calls are unresolved
            pending_ids = {tc.get("id") for tc in tool_calls if isinstance(tc, dict) and tc.get("id")}
            resolved_ids = {
                m.get("tool_call_id")
                for m in context
                if m.get("role") == "tool" and m.get("tool_call_id")
            }
            if pending_ids - resolved_ids:
                return True
    return False


def _compress_conversation_summary_impl(
    current_context: list[dict],
    target_size_bytes: int,
    verbose: bool,
    audit_writer: Any,
    actions: list[str],
    step_name: str,
    **kwargs,
) -> tuple[list[dict], str]:
    """Core conversation summary — condense entire conversation into a single summary message."""
    original_size = _calculate_context_bytes(current_context)

    # Extract system message
    system_msg = current_context[0] if current_context and current_context[0].get("role") == "system" else None

    # Build interaction pairs
    interactions: list[str] = []
    current_user_content: str | None = None
    current_assistant_content: str | None = None
    current_tool_lines: list[str] = []
    interaction_num = 0

    i = 0
    # Skip system message
    if current_context and current_context[0].get("role") == "system":
        i = 1

    while i < len(current_context):
        msg = current_context[i]
        role = msg.get("role", "")

        if role == "user":
            # Save previous interaction if exists
            if current_user_content is not None:
                interaction_num += 1
                interaction_lines = [f"### INTERACTION {interaction_num}"]
                # Check if synthetic
                if is_synthetic_message(msg):
                    cat = _extract_synthetic_category(msg)
                    interaction_lines.append(f"**USER:** [SYSTEM: {cat}]")
                else:
                    content = _extract_text_from_content(msg.get("content", ""))
                    interaction_lines.append(f"**USER:** {content}")
                if current_assistant_content:
                    interaction_lines.append(f"**ASSISTANT:** {current_assistant_content}")
                if current_tool_lines:
                    interaction_lines.append("**TOOLS:**\n" + "\n".join(current_tool_lines))
                interactions.append("\n".join(interaction_lines))

            # Start new interaction
            if is_synthetic_message(msg):
                cat = _extract_synthetic_category(msg)
                current_user_content = f"[SYSTEM: {cat}]"
            else:
                current_user_content = _extract_text_from_content(msg.get("content", ""))
            current_assistant_content = None
            current_tool_lines = []

        elif role == "assistant":
            content = _extract_text_from_content(msg.get("content", ""))
            if content:
                current_assistant_content = content
            # Capture tool calls
            for tc in _get_tool_calls_for_assistant(msg):
                if isinstance(tc, dict):
                    func = tc.get("function", {})
                    func_name = func.get("name", "unknown") if isinstance(func, dict) else "unknown"
                    current_tool_lines.append(f"  CALL: {func_name}")

        elif role == "tool":
            content = _extract_text_from_content(msg.get("content", ""))
            tool_name = msg.get("name", "tool")
            # Truncate oversized tool results
            if len(content) > SUMMARY_TOOL_RESULT_MAX_BYTES:
                content = content[:SUMMARY_TOOL_RESULT_MAX_BYTES] + f"\n  [... truncated, {len(content) - SUMMARY_TOOL_RESULT_MAX_BYTES} chars omitted ...]"
            current_tool_lines.append(f"  RESULT ({tool_name}): {content}")

        i += 1

    # Build the summary content
    summary_parts = ["## CONVERSATION HISTORY\n", "The following is a compressed record of our conversation. Each pair shows a user request and the assistant's response.\n"]

    for interaction in interactions:
        summary_parts.append(interaction + "\n\n")

    # Add CURRENT TASK section
    summary_parts.append("### CURRENT TASK\n")
    if current_user_content is not None:
        summary_parts.append(f"**USER:** {current_user_content}\n")
        if current_assistant_content:
            summary_parts.append(f"**ASSISTANT:** {current_assistant_content}\n")
        if current_tool_lines:
            summary_parts.append("**TOOLS:**\n" + "\n".join(current_tool_lines) + "\n")
        # Check if within a turn
        if _is_within_turn(current_context):
            summary_parts.append("**STATUS:** in-progress\n")
        else:
            summary_parts.append("**STATUS:** awaiting response\n")
    else:
        summary_parts.append("**USER:** (no user message found)\n")
        summary_parts.append("**STATUS:** unknown\n")

    summary_content = "\n".join(summary_parts)

    # Build result context
    new_context: list[dict] = []
    if system_msg:
        new_context.append(system_msg)
    new_context.append({"role": "user", "content": summary_content})

    # If not within a turn, add synthetic assistant message
    if not _is_within_turn(current_context):
        new_context.append({
            "role": "assistant",
            "content": "I've summarized our conversation above. What would you like to do next?",
        })

    new_bytes = _calculate_context_bytes(new_context)
    msgs_after = len(new_context)
    action_desc = f"conversation summary: {len(current_context)} msgs ({original_size}B) → {msgs_after} msgs ({new_bytes}B)"
    actions.append(action_desc)

    if verbose:
        _verbose(f"  :: CONVERSATION SUMMARY: {len(current_context)} msgs → {msgs_after} msgs, {original_size:,}B → {new_bytes:,}B")

    return new_context, "SUMMARIZED"


def compress_conversation_summary(
    context: list[dict],
    client,
    model_name: str,
    target_size_bytes: int,
    verbose: bool = False,
    audit_writer: Any = None,
    **kwargs,
) -> tuple[list[dict], dict]:
    """Condense entire conversation into a single summary user message.

    Deterministic restructuring — no LLM call required.
    Preserves ALL interaction history in a compact structured format.
    Result is always OpenAI-alternation-compliant:
        [system_msg, summary_user_msg] or
        [system_msg, summary_user_msg, synthetic_assistant_msg]
    """
    return _compress_wrapper("CONVERSATION_SUMMARY", _compress_conversation_summary_impl, context, target_size_bytes, verbose, audit_writer, **kwargs)


# --- Algorithm 10: Blind Truncation (guaranteed to fit) ---


def _compress_blind_truncate_impl(
    current_context: list[dict],
    target_size_bytes: int,
    verbose: bool,
    audit_writer: Any,
    actions: list[str],
    step_name: str,
    **kwargs,
) -> tuple[list[dict], str]:
    """Core blind truncation — truncate summary message from the beginning."""
    original_size = _calculate_context_bytes(current_context)

    # Find the summary user message
    user_msg_idx = None
    for i, msg in enumerate(current_context):
        if msg.get("role") == "user":
            user_msg_idx = i
            break

    if user_msg_idx is None:
        return current_context, "NO_USER_MSG"

    user_msg = current_context[user_msg_idx]
    content = user_msg.get("content", "")
    if not isinstance(content, str):
        return current_context, "NOT_STRING"

    # Find the CURRENT TASK section
    current_task_marker = "### CURRENT TASK"
    current_task_pos = content.find(current_task_marker)

    # Calculate system message size (if exists)
    system_msg = current_context[0] if current_context and current_context[0].get("role") == "system" else None
    system_bytes = _calculate_context_bytes([system_msg]) if system_msg else 0

    # Target for the user message content (subtract system and overhead)
    overhead = len(json.dumps({"role": "user", "content": ""}))
    user_target = max(100, target_size_bytes - system_bytes - overhead)

    # Truncate from the beginning if needed
    content_bytes = len(content.encode("utf-8"))
    if content_bytes <= user_target:
        return current_context, "ALREADY_FITS"

    # Need to truncate — preserve CURRENT TASK section
    current_task_section = ""
    if current_task_pos >= 0:
        current_task_section = content[current_task_pos:]
        content_to_truncate = content[:current_task_pos]
    else:
        current_task_section = ""
        content_to_truncate = content

    # Calculate how many bytes we can keep from the beginning
    current_task_bytes = len(current_task_section.encode("utf-8"))
    truncation_marker = "[... truncated ...]\n"
    marker_bytes = len(truncation_marker.encode("utf-8"))
    available_for_history = max(0, user_target - current_task_bytes - marker_bytes)

    if available_for_history <= 0:
        new_content = current_task_section
    else:
        # Truncate from the end of the history portion using byte-slice (O(1))
        truncation_point = min(available_for_history, len(content_to_truncate.encode("utf-8")))
        truncated = content_to_truncate.encode("utf-8")[:truncation_point].decode("utf-8", errors="ignore")
        new_content = truncated + truncation_marker + current_task_section

    # Update the message
    new_context = list(current_context)
    new_context[user_msg_idx] = {**user_msg, "content": new_content}

    new_bytes = _calculate_context_bytes(new_context)
    chars_removed = len(content) - len(new_content)
    action_desc = f"blind truncate: removed {chars_removed} chars from beginning, {original_size}B → {new_bytes}B"
    actions.append(action_desc)

    if verbose:
        _verbose(f"  :: BLIND TRUNCATE: {chars_removed} chars removed, {original_size:,}B → {new_bytes:,}B")

    return new_context, "TRUNCATED"


def compress_blind_truncate(
    context: list[dict],
    client,
    model_name: str,
    target_size_bytes: int,
    verbose: bool = False,
    audit_writer: Any = None,
    **kwargs,
) -> tuple[list[dict], dict]:
    """Last-resort: truncate summary message from the beginning.

    Guaranteed to produce a context that fits within target_size_bytes.
    Preserves the most recent information (right side).
    Adds a marker indicating truncation occurred.
    """
    return _compress_wrapper("BLIND_TRUNCATE", _compress_blind_truncate_impl, context, target_size_bytes, verbose, audit_writer, **kwargs)



# --- Pipeline Registry ---

# Pipeline references impl functions directly.  ``_compress_wrapper`` is called
# in the orchestrator loop, forwarding ``step.kwargs`` to each impl.  The public
# wrapper functions (``compress_*``) are kept for backward-compatible testing.

_COMPRESSION_PIPELINE: tuple[CompressionStep, ...] = (
    CompressionStep("PRUNE_IMAGES", _compress_prune_images_impl),
    CompressionStep("OVERSIZED_TOOL_REDACTION", _compress_oversized_tool_redaction_impl),
    CompressionStep("DROP_REASONING", _compress_drop_reasoning_impl),
    CompressionStep("LAST_TRANSACTION", _compress_last_transaction_impl),
    CompressionStep("TOOL_PRUNING", _compress_tool_pruning_impl, kwargs={"use_boundary": True}),
    CompressionStep("REDACT_BLOCKS", _compress_redact_blocks_impl, kwargs={"use_boundary": True}),
    CompressionStep("TOOL_PRUNING_FULL", _compress_tool_pruning_impl, kwargs={"use_boundary": False}),
    CompressionStep("REDACT_BLOCKS_FULL", _compress_redact_blocks_impl, kwargs={"use_boundary": False}),
    CompressionStep("FULL_RESET", _compress_full_reset_impl),
    CompressionStep("CONVERSATION_SUMMARY", _compress_conversation_summary_impl),
    CompressionStep("BLIND_TRUNCATE", _compress_blind_truncate_impl),
)

# --- Orchestrator ---
def compress_context(
    context: list[dict],
    client,
    model_name: str,
    compression_factor: float,
    tools: list,
    extra_kwargs: dict | None = None,
    verbose: bool = False,
    log_file: Path | None = None,
    audit_writer: Any = None,
    last_known_tokens: int | None = None,
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> tuple[list[dict], str, dict[str, Any]]:
    """Run compression algorithms in sequence until target size is reached.

    Pipeline (least to most aggressive):
    1.  PRUNE_IMAGES — replace image content blocks with text placeholders
    2.  OVERSIZED_TOOL_REDACTION — redact single oversized tool results
    3.  DROP_REASONING — strip reasoning fields from assistant messages
    4.  LAST_TRANSACTION — LLM summarization of completed turns
    5.  TOOL_PRUNING — replace large tool outputs with placeholders (50% boundary)
    6.  REDACT_BLOCKS — strip intermediate messages from completed blocks (50% boundary)
    7.  TOOL_PRUNING_FULL — same as #5 but scans entire context (no boundary)
    8.  REDACT_BLOCKS_FULL — same as #6 but scans entire context (no boundary)
    9.  FULL_RESET — full context rebuild (last resort)
    10. CONVERSATION_SUMMARY — deterministic conversation restructuring (fallback)
    11. BLIND_TRUNCATE — truncate summary from beginning (guaranteed fit)

    Stops early if target is reached.  Original context preserved if all fail.
    """
    original_size = _calculate_context_bytes(context)
    original_message_count = len(context)
    target_size = compute_compression_target_bytes(
        original_size,
        compression_factor,
        last_known_tokens,
        max_context_tokens,
        max_output_tokens,
    )

    if audit_writer is not None:
        audit_writer.compress_pipeline_start(original_size, target_size, compression_factor, last_known_tokens)

    if verbose:
        byte_target = int(original_size * (1 - compression_factor))
        if last_known_tokens is not None and last_known_tokens > 0:
            echo(f"[COMPRESS] ORCHESTRATOR: {original_message_count} msgs, {original_size:,} bytes → target {compression_factor*100:.0f}% ({byte_target:,} bytes), token-aware target: {target_size:,} bytes (tokens: {last_known_tokens})")
        else:
            echo(f"[COMPRESS] ORCHESTRATOR: {original_message_count} msgs, {original_size:,} bytes → target {compression_factor*100:.0f}% ({target_size:,} bytes)")

    result = list(context)
    algorithms_used: list[str] = []
    bytes_per_algo: dict[str, int] = {}

    total_steps = len(_COMPRESSION_PIPELINE)

    for idx, step in enumerate(_COMPRESSION_PIPELINE, 1):
        # Forward all params so LLM-based steps (last_transaction, full_reset)
        # can reach _invoke_llm_with_retry_compression via kwargs
        result, step_metadata = _compress_wrapper(
            step.name, step.impl_fn, result, target_size, verbose, audit_writer,
            client=client, model_name=model_name, tools=tools,
            extra_kwargs=extra_kwargs, log_file=log_file,
            max_context_tokens=max_context_tokens,
            max_output_tokens=max_output_tokens,
            **step.kwargs,
        )
        size = step_metadata["bytes_after"]
        msg_count = step_metadata["msgs_after"]
        action_summary = _build_action_summary(step_metadata["actions"])

        # Always emit console one-liner for this step
        compression_step_summary(
            step_name=step_metadata["step_name"],
            step_idx=idx,
            total_steps=total_steps,
            bytes_before=step_metadata["bytes_before"],
            msgs_before=step_metadata["msgs_before"],
            bytes_after=step_metadata["bytes_after"],
            msgs_after=step_metadata["msgs_after"],
            action_summary=action_summary,
            status=step_metadata["status"],
        )

        if verbose:
            _verbose(f"[STEP {idx}/{total_steps} {step.name}] Entry: {step_metadata['msgs_before']} msgs, {step_metadata['bytes_before']:,} bytes")
            _verbose(f"[STEP {idx}/{total_steps} {step.name}] Exit: {msg_count} msgs, {size:,} bytes")

        algorithms_used.append(step.name)
        bytes_per_algo[step.name] = step_metadata["bytes_before"] - step_metadata["bytes_after"]

        if size <= target_size:
            # Debug: log why we're exiting early
            echo(f"[COMPRESS] EARLY EXIT at step {idx}/{total_steps} ({step.name}): size={size:,} <= target={target_size:,} (reduction={(1-size/original_size)*100:.1f}%, target={compression_factor*100:.0f}%)")
            summary, metadata = _format_success(
                step.name, size, original_size, compression_factor, msg_count,
                algorithms_used, verbose,
            )
            return result, summary, metadata

    # All steps exhausted — return final result
    echo(f"[COMPRESS] ALL STEPS EXHAUSTED: size={size:,} > target={target_size:,} (reduction={(1-size/original_size)*100:.1f}%, target={compression_factor*100:.0f}%)")
    if verbose and bytes_per_algo:
        for algo_name, saved in bytes_per_algo.items():
            _verbose(f"  :: {algo_name}: saved {saved:,} bytes")

    final_summary = f"FINAL: {algorithms_used[-1] if algorithms_used else 'NONE'} ({size:,} bytes)"

    if verbose:
        echo(f"\n{'='*70}")
        echo("  COMPRESSION COMPLETE - FINAL")
        echo(f"{'='*70}\n")
        reduction_pct = (1 - size / original_size) * 100 if original_size > 0 else 0
        _verbose(f"    Original: {original_size:,} bytes -> {size:,} bytes")
        _verbose(f"    Reduction: {reduction_pct:.1f}% (target was {compression_factor*100:.0f}%)")
        _verbose(f"    Algorithms used: {' + '.join(algorithms_used)}")
        _verbose(f"    Final context: {size:,} bytes, {msg_count} messages\n")

    metadata = {
        "bytes_before": original_size,
        "bytes_after": size,
        "algorithms_used": algorithms_used,
        "bytes_per_algo": bytes_per_algo,
    }

    # --- Final verification: print error if target not achieved ---
    if size > target_size:
        echo(
            f"\n{'='*70}\n"
            f"  COMPRESSION TARGET NOT MET — ROOT CAUSE INVESTIGATION\n"
            f"{'='*70}\n"
            f"  Original size:   {original_size:,} bytes\n"
            f"  Target size:     {target_size:,} bytes (compression_factor={compression_factor})\n"
            f"  Achieved size:   {size:,} bytes\n"
            f"  Reduction:       {(1-size/original_size)*100:.1f}% (need {compression_factor*100:.0f}%)\n"
            f"  Gap:             {size - target_size:,} bytes above target\n"
            f"  Algorithms used: {' + '.join(algorithms_used)}\n"
            f"  Bytes saved:     {sum(bytes_per_algo.values()):,} bytes\n"
            f"{'='*70}\n"
        )
        if audit_writer is not None:
            audit_writer.compress_pipeline_end(size, algorithms_used, sum(bytes_per_algo.values()))

    return result, final_summary, metadata
