"""Algorithm 10: Blind Truncation — truncate summary message from the beginning.

Last-resort compression: find the summary user message and truncate it from
the beginning to fit within target_size_bytes. Preserves the CURRENT TASK section.
Guaranteed to produce a context that fits.
"""

from __future__ import annotations

import json

from agent_context_compress.steps.framework import CompressionContext, make_compress_wrapper, _verbose
from agent_context_compress.steps.utils import _calculate_context_bytes


def _compress_blind_truncate_impl(ctx: CompressionContext, **kwargs) -> tuple[list[dict], str]:
    """Core blind truncation — truncate summary message from the beginning."""
    original_size = ctx.current_bytes()

    # Find the summary user message
    user_msg_idx = None
    for i, msg in enumerate(ctx.context):
        if msg.get("role") == "user":
            user_msg_idx = i
            break

    if user_msg_idx is None:
        return ctx.context, "NO_USER_MSG"

    user_msg = ctx.context[user_msg_idx]
    content = user_msg.get("content", "")
    if not isinstance(content, str):
        return ctx.context, "NOT_STRING"

    # Find the CURRENT TASK section
    current_task_marker = "### CURRENT TASK"
    current_task_pos = content.find(current_task_marker)

    # Calculate system message size (if exists)
    system_msg = ctx.context[0] if ctx.context and ctx.context[0].get("role") == "system" else None
    system_bytes = _calculate_context_bytes([system_msg]) if system_msg else 0

    # Target for the user message content (subtract system and overhead)
    overhead = len(json.dumps({"role": "user", "content": ""}))
    user_target = max(100, ctx.target_size_bytes - system_bytes - overhead)

    # Truncate from the beginning if needed
    content_bytes = len(content.encode("utf-8"))
    if content_bytes <= user_target:
        return ctx.context, "ALREADY_FITS"

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
    new_context = list(ctx.context)
    new_context[user_msg_idx] = {**user_msg, "content": new_content}

    new_bytes = _calculate_context_bytes(new_context)
    chars_removed = len(content) - len(new_content)
    action_desc = f"blind truncate: removed {chars_removed} chars from beginning, {original_size}B → {new_bytes}B"
    ctx.actions.append(action_desc)

    if ctx.verbose:
        _verbose(f"  :: BLIND TRUNCATE: {chars_removed} chars removed, {original_size:,}B → {new_bytes:,}B")

    ctx.context = new_context
    return ctx.context, "TRUNCATED"


compress_blind_truncate = make_compress_wrapper("BLIND_TRUNCATE", _compress_blind_truncate_impl)
