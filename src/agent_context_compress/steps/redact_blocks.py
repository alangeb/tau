"""Algorithm 3/7: Redact Blocks — strip intermediate messages from completed blocks.

Find completed user-assistant blocks and remove intermediate messages
(tool calls, tool results), keeping only the user and final assistant message.
Can operate within 50% boundary or scan entire context.
"""

from __future__ import annotations

from agent_console import echo, error
from agent_message_utils import is_synthetic_message
from agent_models import Colors

from agent_context_compress.steps.framework import CompressionContext, make_compress_wrapper, _verbose
from agent_context_compress.steps.utils import (
    MAX_ITERATIONS,
    MIN_BLOCK_SIZE,
    _calculate_context_bytes,
    _has_orphaned_tool_results,
    _has_unresolved_tool_calls,
)


def _compress_redact_blocks_impl(ctx: CompressionContext, use_boundary: bool = True, **kwargs) -> tuple[list[dict], str]:
    """Core block redaction logic.

    Args:
        use_boundary: If True, redact only within 50% boundary. If False, redact entire context.
    """
    iteration = 0
    while not ctx.at_target():
        iteration += 1
        if iteration > MAX_ITERATIONS:
            if ctx.verbose:
                error("  :: ITERATION LIMIT REACHED (100), STOPPING")
            break

        if ctx.verbose:
            echo(f"{Colors.YELLOW}{'-'*70}{Colors.RESET}")
            echo(
                f"  :: ITERATION #{iteration} START: current_size={ctx.current_bytes():,} bytes, target={ctx.target_size_bytes:,} bytes"
            )

        # Recompute scan limit each iteration (context shrinks as blocks are redacted)
        if use_boundary:
            _, boundary_idx = ctx.boundary()
            scan_limit = boundary_idx
        else:
            scan_limit = len(ctx.context)

        found_block = False
        i = 0
        while i <= scan_limit:
            # Safety: break if i exceeds current context length (can happen after redaction)
            if i >= len(ctx.context):
                break
            if ctx.context[i].get("role") == "user" and not is_synthetic_message(ctx.context[i]):
                user_idx = i
                assistant_idx = None

                for j in range(i + 1, scan_limit):
                    if ctx.context[j].get("role") == "user" and not is_synthetic_message(ctx.context[j]):
                        break
                    if ctx.context[j].get("role") == "assistant" and not ctx.context[j].get("tool_calls"):
                        assistant_idx = j
                        break

                if assistant_idx is not None:
                    block = ctx.context[user_idx:assistant_idx + 1]
                    block_bytes = _calculate_context_bytes(block)

                    if block_bytes < MIN_BLOCK_SIZE:
                        if ctx.verbose:
                            _verbose(f"     ✗ Block too small (< {MIN_BLOCK_SIZE} bytes) - SKIP")
                        i = assistant_idx + 1
                        continue

                    if _has_unresolved_tool_calls(block):
                        if ctx.verbose:
                            _verbose("     ✗ Block contains unresolved tool calls - SKIP")
                        i = assistant_idx + 1
                        continue

                    if _has_orphaned_tool_results(block):
                        if ctx.verbose:
                            _verbose("     ✗ Block contains orphaned tool results - SKIP")
                        i = assistant_idx + 1
                        continue

                    removed_count = len(block) - 2
                    new_block = [
                        ctx.context[user_idx],
                        ctx.context[assistant_idx],
                    ]
                    new_bytes = _calculate_context_bytes(new_block)
                    savings = block_bytes - new_bytes
                    action_desc = f"redacted block [{user_idx}:{assistant_idx}]: {block_bytes}B → {new_bytes}B (removed {removed_count} intermediates)"
                    ctx.add_action(action_desc, action_type="redact_block")

                    if ctx.verbose:
                        _verbose(f"  :: BLOCK #{user_idx}-{assistant_idx} REDACTED: SAVED {savings:,} bytes (removed {removed_count} intermediates)")

                    ctx.context = (
                        ctx.context[:user_idx]
                        + new_block
                        + ctx.context[assistant_idx + 1:]
                    )
                    found_block = True
                    break

            i += 1

        if not found_block:
            if ctx.verbose:
                boundary_msg = "within boundary" if use_boundary else "in context"
                _verbose(f"  :: No more completed blocks to redact {boundary_msg}")
            break

    final_size = ctx.current_bytes()
    status = "ACHIEVED" if ctx.at_target() else "NO_MORE_BLOCKS"
    return ctx.context, status


compress_redact_blocks = make_compress_wrapper(
    lambda kw: "REDACT_BLOCKS" if kw.get("use_boundary", True) else "REDACT_BLOCKS_FULL",
    _compress_redact_blocks_impl,
)
