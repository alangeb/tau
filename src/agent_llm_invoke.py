"""LLM invocation with retry logic and context overflow handling.

Extracted from agent_llm.py — contains _invoke_llm_with_retry and supporting helpers.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agent_console import (
    error_display,
    llm_timeout_message,
    llm_validation_retry,
    warning,
)
from agent_model_health import get_health_monitor
from agent_llm_models import (
    ALLOWED_MESSAGE_FIELDS,
    _ALLOWED_TOOL_CALL_FIELDS,
    APITimeoutError,
    BadRequestError,
    CallStats,
    COMPRESSION_TARGET_RATIO,
    DEFAULT_MAX_CONTEXT_TOKENS,
    DEFAULT_MAX_OUTPUT_TOKENS,
    EmptyModelResponse,
    LLMCallConfig,
    LLMResponse,
    OPENAI_BODY_PARAMS,
    OVERSIZED_THRESHOLD,
)
from agent_llm_client import _is_context_overflow
from agent_llm_tool_parse import (
    BEGIN_OF_THOUGHT,
    END_OF_THOUGHT,
    llm_postparse,
)
from agent_llm_validation import (
    InvalidReplyError,
    _strip_phantoms,
    llm_validate,
)

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Stats extraction
# ---------------------------------------------------------------------------

def _extract_call_stats(response: Any, response_text: str) -> CallStats:
    """Extract token usage and finish_reason from LLM response.

    Returns ``None`` for token fields when the API provides no usage data,
    so callers can distinguish "API returned 0" from "API returned no data".
    """
    usage = getattr(response, "usage", None)

    if usage:
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        pt_details = getattr(usage, "prompt_tokens_details", None)
        # Distinguish "API returned 0 cached" from "API didn't report cached".
        cached_tokens = pt_details.get("cached_tokens", 0) if isinstance(pt_details, dict) else None
    else:
        prompt_tokens = completion_tokens = cached_tokens = None

    finish_reason = None
    choices = getattr(response, "choices", None)
    if choices:
        finish_reason = getattr(choices[0], "finish_reason", None)

    return CallStats(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cached_tokens=cached_tokens,
        finish_reason=finish_reason,
    )


def _extract_token_usage(response: Any, response_text: str) -> tuple[int, int, int]:
    """Legacy wrapper: returns (prompt_tokens, completion_tokens, cached_tokens)."""
    stats = _extract_call_stats(response, response_text)
    return (stats.prompt_tokens, stats.completion_tokens, stats.cached_tokens)


# ---------------------------------------------------------------------------
# Internal helpers for _invoke_llm_with_retry
# ---------------------------------------------------------------------------

def _prepare_messages(messages: Any) -> list[dict]:
    """Normalize messages: merge reasoning, strip non-API fields.

    Works on the REAL message list (no copy) so compression is in-place.
    """
    msg_list = messages.to_list() if hasattr(messages, "to_list") else messages
    # Shallow copy of list (not deep copy) — isolates mutations from caller's list
    # while allowing in-place compression to modify message dicts directly.
    msg_list = list(msg_list)

    # Merge reasoning into content with thinking markers (vLLM ignores top-level "reasoning").
    for msg in msg_list:
        reasoning = msg.pop("reasoning", None)
        if reasoning:
            content = msg.get("content", "")
            if isinstance(content, list):
                # Multimodal content — prepend reasoning as a text block.
                # Gemma 4 wants images BEFORE text, so insert reasoning block
                # before the first text block (after any image_url blocks).
                reasoning_block = {
                    "type": "text",
                    "text": f"{BEGIN_OF_THOUGHT}{reasoning}{END_OF_THOUGHT}",
                }
                # Find first text block index to insert before
                first_text_idx = next(
                    (i for i, p in enumerate(content) if p.get("type") == "text"),
                    0,
                )
                msg["content"] = (
                    content[:first_text_idx]
                    + [reasoning_block]
                    + content[first_text_idx:]
                )
            else:
                msg["content"] = f"{BEGIN_OF_THOUGHT}{reasoning}{END_OF_THOUGHT}\n{content or ''}"

    # Strip non-OpenAI fields from messages and nested tool_calls.
    for msg in msg_list:
        for key in list(msg.keys()):
            if key not in ALLOWED_MESSAGE_FIELDS:
                msg.pop(key, None)
        for tc in msg.get("tool_calls") or []:
            if isinstance(tc, dict):
                for key in list(tc.keys()):
                    if key not in _ALLOWED_TOOL_CALL_FIELDS:
                        tc.pop(key, None)

    return msg_list


def _build_call_kwargs(
    model_name: str,
    messages: list[dict],
    tools: list,
    tool_choice: str,
    stream: bool,
    extra_kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Build the kwargs dict for client.chat.completions.create()."""
    call_kwargs: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "tools": tools,
        "tool_choice": tool_choice,
        "stream": stream,
    }

    if not extra_kwargs:
        return call_kwargs

    # Split: standard params -> body, non-standard -> extra_body (+ body for llama.cpp compat).
    body_updates: dict[str, Any] = {}
    extra_body: dict[str, Any] = {}

    for k, v in extra_kwargs.items():
        if k == "_extra_body":
            extra_body = v
        elif k in OPENAI_BODY_PARAMS:
            body_updates[k] = v
        else:
            extra_body[k] = v
            body_updates[k] = v

    if "repetition_penalty" in extra_body:
        body_updates["repeat_penalty"] = extra_body["repetition_penalty"]

    call_kwargs.update(body_updates)
    if extra_body:
        call_kwargs["extra_body"] = extra_body

    return call_kwargs


# [REMOVED] _truncate_largest_message — replaced by in-place compression.

# ---------------------------------------------------------------------------
# Public API — _invoke_llm_with_retry
# ---------------------------------------------------------------------------

def _build_llm_response(
    response: Any,
    response_text: str,
    reasoning_content: str | None,
    call_stats: CallStats,
    tool_calls: list[dict],
    success: bool,
) -> LLMResponse:
    """Construct an LLMResponse from the common response components."""
    return LLMResponse(
        raw=response,
        text=response_text,
        reasoning=reasoning_content,
        stats=call_stats,
        success=success,
        tool_calls=tool_calls,
    )


# ---------------------------------------------------------------------------
# Overflow compression helpers — invoked before naive truncation
# ---------------------------------------------------------------------------


def _try_oversized_redaction(msg_list: list[dict]) -> list[dict] | None:
    """Redact tool results that exceed OVERSIZED_THRESHOLD of total context bytes.

    Returns a NEW list with redacted content if any redaction occurred, else None.
    Uses json.dumps for accurate byte counting (handles multimodal list content).
    """
    total_bytes = sum(len(json.dumps(m.get("content", ""))) for m in msg_list)
    threshold = int(total_bytes * OVERSIZED_THRESHOLD)
    redacted = False
    result: list[dict] = []

    for msg in msg_list:
        if msg.get("role") == "tool":
            content = msg.get("content", "")
            content_bytes = len(json.dumps(content))
            if content_bytes > threshold:
                result.append({
                    **msg,
                    "content": f"[redacted tool result: {content_bytes} bytes]",
                })
                redacted = True
                continue
        result.append(msg)

    return result if redacted else None


def _try_context_compress(
    msg_list: list[dict],
    client: Any,
    model_name: str,
    tools: list | None,
    extra_kwargs: dict | None,
    log_file: Path | None,
    audit_writer: Any,
    last_known_tokens: int | None = None,
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> list[dict] | None:
    """Invoke the full compression pipeline on the message list.

    Returns compressed messages, or None on failure (best-effort fallback).
    """
    if client is None:
        return None

    try:
        from agent_context_compress import compress_context

        compressed, _summary, _meta = compress_context(
            msg_list,
            client,
            model_name,
            COMPRESSION_TARGET_RATIO,
            tools or [],
            extra_kwargs,
            log_file=log_file,
            audit_writer=audit_writer,
            last_known_tokens=last_known_tokens,
            max_context_tokens=max_context_tokens,
            max_output_tokens=max_output_tokens,
        )
        return compressed
    except Exception:
        return None


def _extract_token_count_from_error(error_str: str) -> int | None:
    """Extract token count from API error messages.

    Parses patterns like:
    - "your prompt contains at least 188001 input tokens"
    - "Request too large. Your prompt contains X tokens"
    """
    import re
    # Match "at least NNNNNN input tokens" or "contains NNNNNN tokens"
    match = re.search(r"(\d+)\s*(?:input\s*)?tokens?", error_str, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _handle_context_overflow(
    msg_list: list[dict],
    config: LLMCallConfig,
    attempt: int,
    error_str: str | None = None,
) -> list[dict] | None:
    """Handle context overflow by escalating: redaction → compression → give up.

    Returns compressed message list if recovery succeeded, None to abort.
    Modifies msg_list in-place when compression succeeds.
    """
    if not msg_list:
        return None

    # Extract token count from error message for token-aware compression
    last_known_tokens = None
    if error_str is not None:
        last_known_tokens = _extract_token_count_from_error(error_str)

    # Escalating overflow strategy:
    #   attempts 0-2: oversized tool redaction (cheap)
    #   attempts 3+: full compress via context (uses LLM)
    compressed = None
    if 0 <= attempt <= 2:
        compressed = _try_oversized_redaction(msg_list)
    else:
        compressed = _try_context_compress(
            msg_list,
            config.compress_client,
            config.compress_model or "",
            config.compress_tools,
            config.compress_extra_kwargs,
            config.log_file,
            config.compress_audit_writer,
            last_known_tokens=last_known_tokens,
            max_context_tokens=config.max_context_tokens,
            max_output_tokens=config.max_output_tokens,
        )

    if compressed is not None:
        return compressed
    return None  # Compression failed — caller should check max_retries


def _is_text_encode_error(error_str: str) -> bool:
    """Detect TextEncodeInput / tokenizer encoding errors.

    These errors mean the context contains invalid characters (e.g., lone
    UTF-16 surrogates) that the tokenizer cannot process. Unlike network
    errors, blind retries are useless — the context must be sanitized.
    """
    return "TextEncodeInput" in error_str or "TextInputSequence" in error_str


def _is_vision_error(error_str: str) -> bool:
    """Detect vision-incompatible model errors.

    Matches vLLM: 'At most 0 image(s) may be provided in one prompt.'
    Also matches generic patterns containing 'image' or 'vision' combined
    with capability keywords (not supported, cannot, may be provided, etc.).
    """
    lower = error_str.lower()
    has_image = "image" in lower
    has_vision = "vision" in lower
    has_capability_keyword = any(
        kw in lower
        for kw in (
            "may be provided", "not supported", "cannot", "can't",
            "unable", "does not support", "do not support", "required",
        )
    )
    return (has_image or has_vision) and has_capability_keyword


def _strip_image_blocks(msg_list: list[dict]) -> list[dict] | None:
    """Strip image_url blocks from multimodal content.

    Returns a NEW list with stripped content if any images were removed,
    else None (no images present).

    Aligns with design 3.10 (pre-API field stripping) and 3.18 (in-place
    compression pattern). Messages that become empty after stripping are
    replaced with a text placeholder to preserve OpenAI alternation
    (design 18.6).
    """
    # Handle TauContext or plain list
    if hasattr(msg_list, "to_list"):
        msg_list = msg_list.to_list()
    msg_list = list(msg_list)

    stripped = False
    result: list[dict] = []

    for msg in msg_list:
        content = msg.get("content")
        if isinstance(content, list):
            # Multimodal content — filter out image_url blocks
            text_blocks = [b for b in content if b.get("type") != "image_url"]
            if len(text_blocks) < len(content):
                stripped = True
                if text_blocks:
                    # Keep remaining text blocks
                    result.append({**msg, "content": text_blocks})
                else:
                    # Pure-image message: replace with placeholder.
                    # Preserves OpenAI alternation (18.6).
                    result.append(
                        {**msg, "content": "[image: model does not support vision]"}
                    )
                continue
        result.append(msg)

    return result if stripped else None


def _invoke_llm_with_retry(
    client: Any,
    model_name: str,
    messages: list,
    tools: list,
    tool_choice: str,
    stream: bool = False,
    config: LLMCallConfig | None = None,
    valid_tool_names: set[str] | None = None,
) -> tuple[LLMResponse, list[dict] | None]:
    """Invoke LLM with retry logic and error handling.

    Returns ``(LLMResponse, compressed_messages)``. The second element is
    ``None`` when no compression occurred, or the compressed message list
    when context overflow triggered compression. Caller must sync the
    compressed messages back to the agent context (e.g.
    ``context.set_messages(compressed)``) to make compression persistent.
    """
    if config is None:
        config = LLMCallConfig()

    # Deep-copy to prevent mutating the caller's config during retries.
    effective_extra = copy.deepcopy(config.extra_kwargs) if config.extra_kwargs else {}
    effective_max_retries = config.max_retries
    effective_disable_after = config.disable_thinking_after
    effective_log_on_failure = config.log_on_failure
    effective_log_file = config.log_file
    effective_min_bytes = config.min_response_bytes

    # Track compressed messages — None means no compression occurred.
    compressed_messages: list[dict] | None = None
    last_error: Exception | None = None
    text_encode_retry_done = False  # Track TextEncodeInput sanitization retry
    consecutive_length_errors = 0  # Track consecutive finish_reason=length

    # Health monitoring — track connection health (advisory, not blocking)
    health_monitor = get_health_monitor()

    for attempt in range(effective_max_retries + 1):
        # Advisory warning if circuit is open — don't block, let retry logic handle backoff
        if not health_monitor.is_healthy():
            status = health_monitor.get_status()
            warning(
                f"  :: LLM circuit OPEN (consecutive_failures={status.consecutive_failures}) — "
                f"proceeding with retry (existing backoff handles wait)"
            )

        # Prepare messages fresh each iteration so compressed context is used.
        msg_list = _prepare_messages(messages)

        # Disable thinking after N retries to force decisive responses.
        if (
            attempt >= effective_disable_after
            and effective_extra
            and effective_extra.get("chat_template_kwargs")
        ):
            effective_extra["chat_template_kwargs"]["enable_thinking"] = False

        try:
            call_kwargs = _build_call_kwargs(
                model_name, msg_list, tools, tool_choice, stream, effective_extra
            )

            response = client.chat.completions.create(**call_kwargs)
            if not response.choices:
                raise EmptyModelResponse("Empty response from model")

            choice = response.choices[0]
            response_text = choice.message.content or ""
            reasoning_content = getattr(choice.message, "reasoning_content", None)
            call_stats = _extract_call_stats(response, response_text)

            # Check minimum response length.
            if effective_min_bytes is not None and len(response_text) < effective_min_bytes:
                last_error = Exception(
                    f"Response too short ({len(response_text)} bytes < {effective_min_bytes} required)"
                )
                warning(
                    f"  :: LLM attempt {attempt + 1}/{effective_max_retries + 1}: "
                    f"response too short"
                )
                continue

            # Convert SDK tool calls to dicts.
            sdk_tool_calls = choice.message.tool_calls or []
            tool_calls_dicts = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in sdk_tool_calls
            ]

            response_text, reasoning_content, _ = llm_postparse(
                response_text, reasoning_content, tool_calls_dicts,
                valid_tool_names=valid_tool_names,
            )

            # Validate reply.
            try:
                llm_validate(
                    response_text,
                    reasoning_content,
                    tool_calls_dicts,
                    call_stats.finish_reason,
                )
            except InvalidReplyError as e:
                # Detect stuck-loop: consecutive finish_reason=length with same context
                if call_stats.finish_reason == "length":
                    consecutive_length_errors += 1
                    if consecutive_length_errors >= 3:
                        # Context too large — compress, then give up if still failing
                        compressed = _try_context_compress(
                            messages,
                            config.compress_client,
                            config.compress_model or "",
                            config.compress_tools,
                            config.compress_extra_kwargs,
                            config.log_file,
                            config.compress_audit_writer,
                        )
                        if compressed is not None:
                            messages = compressed
                            compressed_messages = compressed
                            continue  # Retry with compressed context
                        # Compression failed — give up
                        return _build_llm_response(
                            response, response_text, reasoning_content,
                            call_stats, tool_calls_dicts,
                            success=False,
                        ), compressed_messages
                    # < 3 consecutive: likely just a long answer, retry normally
                else:
                    consecutive_length_errors = 0  # Reset on non-length error

                if attempt >= effective_max_retries:
                    # Retries exhausted — if this was a phantom detection,
                    # strip phantoms silently before returning.
                    if "phantom tool-call-like" in str(e):
                        response_text, reasoning_content = _strip_phantoms(
                            response_text, reasoning_content,
                        )
                    return _build_llm_response(
                        response,
                        response_text,
                        reasoning_content,
                        call_stats,
                        tool_calls_dicts,
                        success=False,
                    ), compressed_messages
                llm_validation_retry(attempt, effective_max_retries, str(e))
                continue

            # Successful validation — reset counter
            consecutive_length_errors = 0
            health_monitor.record_success()
            return _build_llm_response(
                response,
                response_text,
                reasoning_content,
                call_stats,
                tool_calls_dicts,
                success=True,
            ), compressed_messages

        except (APITimeoutError, TimeoutError, EmptyModelResponse) as e:
            last_error = e

            if attempt >= effective_max_retries:
                error_display("MODEL ERROR", str(e))
                if effective_log_on_failure:
                    from agent_session import log_failed_api_request

                    log_failed_api_request(call_kwargs, effective_log_file)
                raise last_error from e

            llm_timeout_message(attempt, effective_max_retries)

        except BadRequestError as e:
            error_str = str(e)

            if _is_context_overflow(error_str):
                if attempt >= effective_max_retries:
                    error_display("CONTEXT OVERFLOW", str(e))
                    raise

                recovered = _handle_context_overflow(messages, config, attempt, error_str)
                if recovered is not None:
                    messages = recovered
                    compressed_messages = recovered
                    continue
                # Compression failed — fall through to error handling
                if attempt >= effective_max_retries:
                    error_display("CONTEXT OVERFLOW", str(e))
                    raise
            elif _is_vision_error(error_str):
                # Vision-incompatible model.
                # If agent is provided with _recover_from_vision_error,
                # use it (pops injected messages, marks tool results as errors).
                # Otherwise, fall back to strip-and-retry.
                agent = config.agent if config is not None else None
                if agent is not None and hasattr(agent, "_recover_from_vision_error"):
                    recovered = agent._recover_from_vision_error()
                    if recovered:
                        # Recovery succeeded — context cleaned, loop will continue.
                        # Signal caller via compressed_messages channel.
                        compressed_messages = agent.context.to_list()
                        warning(
                            "  :: Model does not support vision — recovered "
                            "context, marking see tool results as errors"
                        )
                        # Fall through to retry with cleaned context
                        messages = compressed_messages
                        continue
                    # Recovery failed — fall through to strip-and-retry
                recovered = _strip_image_blocks(messages)
                if recovered is not None:
                    messages = recovered
                    compressed_messages = recovered
                    warning(
                        "  :: Model does not support vision — stripped image "
                        "blocks from context, retrying"
                    )
                    continue
                # No images to strip — fatal error
                error_display("VISION ERROR", str(e))
                if effective_log_on_failure:
                    from agent_session import log_failed_api_request
                    log_failed_api_request(call_kwargs, effective_log_file)
                raise
            elif _is_text_encode_error(error_str):
                # TextEncodeInput error — context likely contains lone surrogates.
                # Sanitize and retry ONCE. Do NOT retry again on second failure.
                if not text_encode_retry_done:
                    text_encode_retry_done = True
                    from agent_message_utils import _sanitize_content, _sanitize_text

                    # Sanitize all messages in-place.
                    target_msgs = (
                        messages
                        if isinstance(messages, list)
                        else messages._messages
                        if hasattr(messages, "_messages")
                        else []
                    )
                    for msg in target_msgs:
                        if msg.get("content") is not None:
                            msg["content"] = _sanitize_content(msg["content"])
                        if msg.get("reasoning") is not None:
                            msg["reasoning"] = _sanitize_text(msg["reasoning"])
                    warning(
                        "  :: TextEncodeInput error — sanitized context "
                        "(stripped lone surrogates), retrying once"
                    )
                    continue
                else:
                    error_display(
                        "TEXT ENCODE ERROR",
                        "Context contains unfixable encoding errors.",
                    )
                    raise RuntimeError(
                        "Context contains unfixable encoding errors. Session terminated."
                    ) from e

            else:
                # Non-overflow, non-vision BadRequestError — no retry
                error_display("BAD REQUEST", str(e))
                if effective_log_on_failure:
                    from agent_session import log_failed_api_request

                    log_failed_api_request(call_kwargs, effective_log_file)
                raise

        except Exception as e:
            last_error = e

            if isinstance(e, (ConnectionRefusedError, BrokenPipeError, ConnectionResetError)):
                # Endpoint unreachable — backoff and retry
                if attempt >= effective_max_retries:
                    error_display("CONNECTION ERROR", str(e))
                    if effective_log_on_failure:
                        from agent_session import log_failed_api_request

                        log_failed_api_request(call_kwargs, effective_log_file)
                    raise last_error from e

                from agent_llm_client import RetryBackoff

                backoff = RetryBackoff(base=5, max_wait=120, jitter=0.3)
                wait = backoff.next_wait(attempt)
                warning(
                    f"  :: LLM attempt {attempt + 1}/{effective_max_retries + 1}: "
                    f"endpoint unreachable — waiting {wait:.0f}s before retry"
                )
                backoff.wait(attempt)
                continue

            # Unexpected error — no retry
            error_display("UNEXPECTED ERROR", str(e))
            if effective_log_on_failure:
                from agent_session import log_failed_api_request

                log_failed_api_request(call_kwargs, effective_log_file)
            raise

    raise RuntimeError(
        f"_invoke_llm_with_retry exited loop without returning "
        f"(effective_max_retries={effective_max_retries}). This should not happen."
    )


__all__ = [
    "_extract_call_stats",
    "_extract_token_usage",
    "_prepare_messages",
    "_build_call_kwargs",
    "_build_llm_response",
    "_try_oversized_redaction",
    "_try_context_compress",
    "_handle_context_overflow",
    "_is_vision_error",
    "_is_text_encode_error",
    "_strip_image_blocks",
    "_invoke_llm_with_retry",
]
