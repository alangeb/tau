"""Algorithm 1: Oversized Tool Redaction — redact tool results >20% of context.

Scan within 50% boundary. For each tool result that exceeds 20% of the
remaining context bytes, replace the content with a redaction placeholder.
"""

from __future__ import annotations

from agent_context_compress.steps.framework import CompressionContext, make_compress_wrapper, _verbose
from agent_context_compress.steps.utils import OVERSIZED_THRESHOLD, _find_50_boundary


def _compress_oversized_tool_redaction_impl(ctx: CompressionContext, **kwargs) -> tuple[list[dict], str]:
    """Core oversized tool redaction — redact tool results >20% of context."""
    original_size = ctx.current_bytes()
    boundary_50_bytes, boundary_idx = ctx.boundary()
    limit = min(boundary_idx, len(ctx.context) - 1)

    i = 0
    while i <= limit:
        msg = ctx.context[i]
        if msg.get("role") == "tool":
            msg_bytes = len(str(msg.get("content", "")))
            rest_bytes = ctx.current_bytes() - msg_bytes
            if rest_bytes > 0 and msg_bytes / rest_bytes > OVERSIZED_THRESHOLD:
                tool_name = msg.get("name", "unknown")
                pct = msg_bytes / rest_bytes * 100
                redacted_content = (
                    f"[REDACTED: {tool_name} result was {msg_bytes} bytes "
                    f"({pct:.1f}% of context). Content removed by compression.]"
                )
                old_bytes = msg_bytes
                ctx.context[i] = {
                    "role": "tool",
                    "content": redacted_content,
                    "tool_call_id": msg.get("tool_call_id", ""),
                    "name": msg.get("name", ""),
                }
                new_bytes = len(str(redacted_content))
                savings = old_bytes - new_bytes
                action_desc = f"redacted tool '{tool_name}' at msg {i}: {old_bytes}B → {new_bytes}B"
                ctx.add_action(action_desc, action_type="redact_tool")
                if ctx.verbose:
                    _verbose(f"  :: REDACTED tool@{i}: {tool_name} {old_bytes:,} -> {new_bytes:,} bytes (saved {savings:,})")
                boundary_50_bytes = original_size // 2
                boundary_idx = _find_50_boundary(ctx.context, boundary_50_bytes)
        i += 1

    final_size = ctx.current_bytes()
    status = "NO_REDUCTION" if final_size == original_size else "REDUCED"
    return ctx.context, status


compress_oversized_tool_redaction = make_compress_wrapper("OVERSIZED_TOOL_REDACTION", _compress_oversized_tool_redaction_impl)
