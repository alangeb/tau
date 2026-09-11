"""Algorithm 4: Full Reset — LLM generates summary + plan, replaces entire context.

Last resort compression. Makes two LLM calls: one for summary, one for next steps.
Replaces the entire context with a compact summary + plan + current user request.
"""

from __future__ import annotations

from agent_llm_models import DEFAULT_MAX_CONTEXT_TOKENS, DEFAULT_MAX_OUTPUT_TOKENS

from agent_console import error
from agent_message_utils import is_synthetic_message

from agent_context_compress.steps.framework import CompressionContext, make_compress_wrapper, _verbose
from agent_context_compress.steps.llm import _invoke_llm_with_retry_compression
from agent_context_compress.steps.utils import _calculate_context_bytes, _extract_text_from_content


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


def _compress_full_reset_impl(ctx: CompressionContext, **kwargs) -> tuple[list[dict], str]:
    """Core full reset — LLM generates summary + plan, replaces entire context."""
    client = kwargs.get("client")
    model_name = kwargs.get("model_name")
    tools = kwargs.get("tools")
    extra_kwargs = kwargs.get("extra_kwargs")
    log_file = kwargs.get("log_file")
    max_context_tokens = kwargs.get("max_context_tokens", DEFAULT_MAX_CONTEXT_TOKENS)
    max_output_tokens = kwargs.get("max_output_tokens", DEFAULT_MAX_OUTPUT_TOKENS)

    original_size = ctx.current_bytes()

    system_msg = ctx.context[0] if ctx.context and ctx.context[0].get("role") == "system" else None

    # Find the last real (non-synthetic) user message — the most recent turn's request
    # Size guard — don't attempt full reset if context would exceed LLM capacity.
    # This prevents recursive overflow: if context is too large for the LLM,
    # sending it for summarization will fail, triggering compression again.
    # Use 70% of max_context_tokens to leave room for the response.
    from agent_context_compress.steps.utils import _calculate_context_bytes

    _context_for_summary_bytes = _calculate_context_bytes(ctx.context)
    _max_llm_input_bytes = int(max_context_tokens * 1.5)  # ~1.5 bytes/token avg
    _safe_input_bytes = int(_max_llm_input_bytes * 0.7)   # Leave 30% for response
    if _context_for_summary_bytes > _safe_input_bytes:
        if ctx.verbose:
            error(
                f"  :: FULL_RESET SKIPPED: context {_context_for_summary_bytes:,}B exceeds "
                f"safe LLM input {_safe_input_bytes:,}B (70% of {max_context_tokens} tokens). "
                f"Falling through to next compression strategy."
            )
        return ctx.context, "SKIPPED_TOO_LARGE"

    last_real_user_idx = None
    for i in range(len(ctx.context) - 1, -1, -1):
        if ctx.context[i].get("role") == "user" and not is_synthetic_message(ctx.context[i]):
            last_real_user_idx = i
            break

    if last_real_user_idx is None:
        if ctx.verbose:
            error("  :: No real user prompt found! Returning unchanged context.")
        return ctx.context, "FAILED_NO_USER"

    last_real_user_content = _extract_text_from_content(ctx.context[last_real_user_idx].get("content", ""))

    # LLM Request 1: summary — include everything up to and including the last real user message
    context_for_summary = (
        [{"role": "system", "content": SUMMARY_PROMPT},
         {"role": "user", "content": "Summarize everything you have done so far:"}]
        + ctx.context[1:last_real_user_idx + 1]
    )

    try:
        resp = _invoke_llm_with_retry_compression(
            client, model_name, context_for_summary, tools, "auto",
            stream=False, extra_kwargs=extra_kwargs, log_file=log_file,
            max_context_tokens=max_context_tokens,
            max_output_tokens=max_output_tokens,
        )
        summary = resp.text.strip() if resp.text else ""
        if ctx.verbose:
            _verbose(f"  :: LLM SUMMARY received ({len(summary):,} bytes)")
    except Exception as e:
        if ctx.verbose:
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
        if ctx.verbose:
            _verbose(f"  :: LLM NEXT STEPS received ({len(plan):,} bytes)")
    except Exception as e:
        if ctx.verbose:
            error(f"  :: LLM NEXT STEPS FAILED: {e}")
        plan = ""

    new_content = f"""# COMPREHENSION SUMMARY

{summary}

# NEXT STEPS & PLAN

{plan}

# CURRENT USER REQUEST

{last_real_user_content}"""

    if not summary and not plan:
        if ctx.verbose:
            error("  :: FULL_RESET FAILED - Both summary and plan empty. Returning unchanged context.")
        return ctx.context, "FAILED_EMPTY"

    new_context = []
    if system_msg:
        new_context.append(system_msg)
    new_context.append({"role": "user", "content": new_content})

    new_bytes = _calculate_context_bytes(new_context)
    msgs_after = len(new_context)
    action_desc = f"full reset: {len(ctx.context)} msgs ({original_size}B) → {msgs_after} msgs ({new_bytes}B)"
    ctx.actions.append(action_desc)

    if ctx.verbose:
        _verbose(f"  :: NEW CONTEXT: {len(new_context)} msgs, {new_bytes:,} bytes (from {len(ctx.context)} msgs)")

    ctx.context = new_context
    return ctx.context, "RESET"


compress_full_reset = make_compress_wrapper("FULL_RESET", _compress_full_reset_impl)
