"""Algorithm 2b/6: Tool Pruning — replace large tool outputs with placeholders.

Scan tool messages and replace content >100 bytes with a placeholder.
Can operate within 50% boundary or scan entire context.
"""

from __future__ import annotations

from agent_console import echo, error
from agent_models import Colors

from agent_context_compress.steps.framework import CompressionContext, make_compress_wrapper, _verbose
from agent_context_compress.steps.utils import MAX_ITERATIONS, PRUNE_THRESHOLD


def _compress_tool_pruning_impl(ctx: CompressionContext, use_boundary: bool = True, **kwargs) -> tuple[list[dict], str]:
    """Core tool pruning logic.

    Args:
        use_boundary: If True, prune only within 50% boundary. If False, prune entire context.
    """
    if use_boundary:
        _, boundary_idx = ctx.boundary()

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

        # Recompute scan limit each iteration (context shrinks as tools are pruned)
        if use_boundary:
            _, boundary_idx = ctx.boundary()
            scan_limit = boundary_idx + 1
        else:
            scan_limit = len(ctx.context)

        for i in range(scan_limit):
            msg = ctx.context[i]
            if msg.get("role") == "tool":
                tool_content = msg.get("content", "")
                tool_bytes = len(str(tool_content))

                if tool_bytes > PRUNE_THRESHOLD:
                    tool_name = msg.get("name", "unknown")
                    if ctx.verbose:
                        _verbose(f"  :: Found prunable tool at msg #{i}, content_size={tool_bytes:,} bytes")

                    ctx.context[i] = {
                        "role": "tool",
                        "content": "COMPRESSION: CALL RESULT NO LONGER AVAILABLE",
                        "tool_call_id": ctx.context[i].get("tool_call_id", ""),
                        "name": ctx.context[i].get("name", ""),
                    }

                    new_bytes = len("COMPRESSION: CALL RESULT NO LONGER AVAILABLE")
                    savings = tool_bytes - new_bytes
                    action_desc = f"pruned tool '{tool_name}' at msg {i}: {tool_bytes}B → {new_bytes}B"
                    ctx.add_action(action_desc, action_type="prune_tool")

                    if ctx.verbose:
                        _verbose(f"  :: TOOL_PRUNED msg #{i}: SAVED {savings:,} bytes")

                    break
        else:
            # No prunable tool found in this iteration
            if ctx.verbose:
                boundary_msg = "within boundary" if use_boundary else "in context"
                _verbose(f"  :: No more tools with content > 100 bytes found {boundary_msg}")
            break

    final_size = ctx.current_bytes()
    status = "ACHIEVED" if ctx.at_target() else "NO_MORE_TOOLS"
    return ctx.context, status


compress_tool_pruning = make_compress_wrapper(
    lambda kw: "TOOL_PRUNING" if kw.get("use_boundary", True) else "TOOL_PRUNING_FULL",
    _compress_tool_pruning_impl,
)
