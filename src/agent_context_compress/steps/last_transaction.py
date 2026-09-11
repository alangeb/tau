"""Algorithm 2: Last Transaction Compression — LLM summarization of completed turns.

Scan right-to-left within 50% boundary. For each completed user-assistant block
with tool calls, call the LLM to summarize the interaction. Replace the block
with a condensed version.
"""

from __future__ import annotations

from agent_llm_models import DEFAULT_MAX_CONTEXT_TOKENS, DEFAULT_MAX_OUTPUT_TOKENS

from agent_console import echo
from agent_models import Colors

from agent_context_compress.steps.framework import CompressionContext, make_compress_wrapper, _verbose
from agent_context_compress.steps.llm import _invoke_llm_with_retry_compression
from agent_context_compress.steps.utils import (
    MAX_ITERATIONS,
    MIN_BLOCK_SIZE,
    _calculate_context_bytes,
    _extract_text_from_content,
    _find_user_assistant_block,
    _has_orphaned_tool_results,
    _has_unresolved_tool_calls,
)


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


def _compress_last_transaction_impl(ctx: CompressionContext, **kwargs) -> tuple[list[dict], str]:
    """Core last transaction compression — LLM summarization of completed turns."""
    client = kwargs.get("client")
    model_name = kwargs.get("model_name")
    tools = kwargs.get("tools")
    extra_kwargs = kwargs.get("extra_kwargs")
    log_file = kwargs.get("log_file")
    max_context_tokens = kwargs.get("max_context_tokens", DEFAULT_MAX_CONTEXT_TOKENS)
    max_output_tokens = kwargs.get("max_output_tokens", DEFAULT_MAX_OUTPUT_TOKENS)

    original_size = ctx.current_bytes()
    blocks_compressed = 0
    blocks_skipped = 0

    boundary_50_bytes, boundary_msg_idx = ctx.boundary()

    if ctx.verbose:
        echo(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
        echo(f"{Colors.CYAN}>>> LAST_TRANSACTION START >>>{Colors.RESET}")
        echo(
            f"{Colors.CYAN}  target={ctx.target_size_bytes:,} bytes, current={ctx.current_bytes():,} bytes, 50%={original_size // 2:,} bytes{Colors.RESET}"
        )
        echo(
            f"{Colors.CYAN}  50% boundary at msg index {boundary_msg_idx} (of {len(ctx.context)-1}){Colors.RESET}"
        )
        echo(f"{Colors.CYAN}{'='*70}{Colors.RESET}")

    pointer = len(ctx.context)

    iteration = 0
    while not ctx.at_target() and iteration < MAX_ITERATIONS:
        iteration += 1

        user_idx, assistant_idx, block_end = _find_user_assistant_block(ctx.context, pointer)

        if user_idx is None:
            if ctx.verbose:
                _verbose(f"  :: Iteration {iteration}: no completed block found before pointer={pointer} - STOP")
            break

        if boundary_msg_idx is not None and user_idx >= boundary_msg_idx:
            blocks_skipped += 1
            if ctx.verbose:
                _verbose(
                    f"  :: Iteration {iteration}: user@{user_idx} at or right of 50% boundary@{boundary_msg_idx} - SKIP, scanning left"
                )
            pointer = user_idx
            continue

        block = ctx.context[user_idx:block_end]
        assistant_tool_part = ctx.context[user_idx + 1:block_end]
        block_bytes = _calculate_context_bytes(block)
        user_msg = ctx.context[user_idx]

        if ctx.verbose:
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
            if ctx.verbose:
                _verbose(f"  :: SKIP (reason: {skip_reason}) - keeping block as-is, moving left")
            pointer = user_idx
            continue

        if ctx.verbose:
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
                if ctx.verbose:
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
                if ctx.verbose:
                    _verbose(
                        f"  :: Compression not beneficial: {block_bytes:,} -> {new_block_bytes:,} bytes - keeping block as-is, moving left"
                    )
                pointer = user_idx
                continue

            savings = block_bytes - new_block_bytes
            blocks_compressed += 1
            action_desc = f"compressed block [{user_idx}:{block_end}]: {block_bytes}B → {new_block_bytes}B (saved {savings}B)"
            ctx.add_action(action_desc, action_type="compress_block")
            if ctx.verbose:
                _verbose(
                    f"  :: COMPRESSED [{user_idx}:{block_end}]: {block_bytes:,} -> {new_block_bytes:,} bytes (saved {savings:,})"
                )
            ctx.context = (
                ctx.context[:user_idx] + new_block + ctx.context[block_end:]
            )

        except Exception as e:
            blocks_skipped += 1
            if ctx.verbose:
                _verbose(f"  :: LLM error: {e} - keeping block as-is, moving left")

        pointer = user_idx

    final_size = ctx.current_bytes()
    status = "ACHIEVED" if ctx.at_target() else "NO_MORE_BLOCKS"

    if ctx.verbose:
        compression_end_msg = f"[COMPRESS] LAST_TRANSACTION: {len(ctx.context)} msgs, {final_size:,} bytes -> target {ctx.target_size_bytes / original_size * 100 if original_size > 0 else 0:.0f}% ({ctx.target_size_bytes:,} bytes) [{status}]"
        _verbose(compression_end_msg)

    return ctx.context, status


compress_last_transaction = make_compress_wrapper("LAST_TRANSACTION", _compress_last_transaction_impl)
