"""Algorithm 1b: Drop Reasoning — strip reasoning fields from assistant messages.

Scan within 50% boundary. For each assistant message with a reasoning field,
remove the reasoning content. Keeps all messages intact — only strips the
reasoning content.
"""

from __future__ import annotations

from agent_context_compress.steps.framework import CompressionContext, make_compress_wrapper, _verbose


def _compress_drop_reasoning_impl(ctx: CompressionContext, **kwargs) -> tuple[list[dict], str]:
    """Core reasoning drop — strip reasoning fields from assistant messages."""
    original_size = ctx.current_bytes()
    boundary_50_bytes, boundary_idx = ctx.boundary()

    for i in range(min(boundary_idx, len(ctx.context))):
        msg = ctx.context[i]
        if msg.get("role") == "assistant" and "reasoning" in msg:
            reasoning_text = msg["reasoning"]
            reasoning_bytes = len(str(reasoning_text))
            del ctx.context[i]["reasoning"]
            action_desc = f"dropped reasoning at msg {i}: {reasoning_bytes}B"
            ctx.add_action(action_desc, action_type="drop_reasoning")
            if ctx.verbose:
                _verbose(f"  :: DROPPED reasoning@{i}: {reasoning_bytes:,} bytes")

    final_size = ctx.current_bytes()
    status = "NO_REDUCTION" if final_size == original_size else "REDUCED"
    return ctx.context, status


compress_drop_reasoning = make_compress_wrapper("DROP_REASONING", _compress_drop_reasoning_impl)
