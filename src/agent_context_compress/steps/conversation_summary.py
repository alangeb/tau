"""Algorithm 9: Conversation Summary — deterministic conversation restructuring.

Condense entire conversation into a single summary user message without LLM calls.
Preserves ALL interaction history in a compact structured format.
Result is always OpenAI-alternation-compliant.
"""

from __future__ import annotations

from agent_message_utils import is_synthetic_message

from agent_context_compress.steps.framework import CompressionContext, make_compress_wrapper, _verbose
from agent_context_compress.steps.utils import (
    SUMMARY_TOOL_RESULT_MAX_BYTES,
    _calculate_context_bytes,
    _extract_text_from_content,
)


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


def _compress_conversation_summary_impl(ctx: CompressionContext, **kwargs) -> tuple[list[dict], str]:
    """Core conversation summary — condense entire conversation into a single summary message."""
    original_size = ctx.current_bytes()

    # Extract system message
    system_msg = ctx.context[0] if ctx.context and ctx.context[0].get("role") == "system" else None

    # Build interaction pairs
    interactions: list[str] = []
    current_user_content: str | None = None
    current_assistant_content: str | None = None
    current_tool_lines: list[str] = []
    interaction_num = 0

    i = 0
    # Skip system message
    if ctx.context and ctx.context[0].get("role") == "system":
        i = 1

    while i < len(ctx.context):
        msg = ctx.context[i]
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
        if _is_within_turn(ctx.context):
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
    if not _is_within_turn(ctx.context):
        new_context.append({
            "role": "assistant",
            "content": "I've summarized our conversation above. What would you like to do next?",
        })

    new_bytes = _calculate_context_bytes(new_context)
    msgs_after = len(new_context)
    action_desc = f"conversation summary: {len(ctx.context)} msgs ({original_size}B) → {msgs_after} msgs ({new_bytes}B)"
    ctx.actions.append(action_desc)

    if ctx.verbose:
        _verbose(f"  :: CONVERSATION SUMMARY: {len(ctx.context)} msgs → {msgs_after} msgs, {original_size:,}B → {new_bytes:,}B")

    ctx.context = new_context
    return ctx.context, "SUMMARIZED"


compress_conversation_summary = make_compress_wrapper("CONVERSATION_SUMMARY", _compress_conversation_summary_impl)
