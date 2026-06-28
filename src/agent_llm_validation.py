"""LLM reply validation for TauErgon.

Validates LLM responses before they are processed. Extracted from agent_llm.py.
"""

from __future__ import annotations

import json

from agent_console import warning


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class InvalidReplyError(Exception):
    """Raised when reply validation finds a retryable contract violation."""


def _validate_tool_call_json(
    _content: str,
    _reasoning: str | None,
    tool_calls: list[dict],
    _finish_reason: str | None = None,
) -> str | None:
    """Ensure every tool call's arguments are valid JSON."""
    for tc in tool_calls:
        args_raw = tc.get("function", {}).get("arguments", "")
        if not isinstance(args_raw, str):
            continue
        try:
            json.loads(args_raw)
        except (json.JSONDecodeError, ValueError):
            name = tc.get("function", {}).get("name", "?")
            dump = json.dumps(tc, ensure_ascii=False)
            if len(dump) > 300:
                dump = dump[:300] + "..."
            return (
                f"tool call arguments are not valid JSON "
                f"(function={name}, likely truncated output) "
                f"| full toolcall: {dump}"
            )
    return None


def _validate_empty_reply(
    content: str,
    _reasoning: str | None,
    tool_calls: list[dict],
    _finish_reason: str | None = None,
) -> str | None:
    """Reject replies with no text content and no tool calls."""
    if tool_calls:
        return None
    if (content or "").strip():
        return None
    return "empty reply (no content, no tool calls)"


def _validate_phantom_tool_calls(
    content: str,
    reasoning: str | None,
    tool_calls: list[dict],
    finish_reason: str | None = None,
) -> str | None:
    """Detect phantom tool-call-like XML tags that postparse missed.

    If detected, raises ``InvalidReplyError`` to trigger a retry (consuming
    from the same retry budget). After retries are exhausted, the caller
    strips phantoms silently.
    """
    from agent_phantom_detect import detect_phantoms, _load_rules

    # Only check if there are no valid tool calls (phantoms only matter
    # when the LLM output text instead of structured tool calls).
    if tool_calls:
        return None

    rules = _load_rules()
    phantoms = detect_phantoms(content, reasoning, rules)
    if not phantoms:
        return None

    tags = ", ".join(f"'{p.tag_name}'" for p in phantoms)
    return f"phantom tool-call-like tags detected ({tags}) — not executed"


def _strip_phantoms(
    content: str,
    reasoning: str | None,
) -> tuple[str, str | None]:
    """Strip all detected phantom tool calls from content and reasoning.

    Called after retries are exhausted. The LLM must NOT see the original
    phantom patterns — they would serve as bad examples and cause repetition.
    """
    from agent_phantom_detect import detect_phantoms, strip_phantoms, _load_rules

    rules = _load_rules()
    phantoms = detect_phantoms(content, reasoning, rules)
    if not phantoms:
        return content, reasoning
    return strip_phantoms(content, reasoning, phantoms)


# Validation pipeline: order matters (most critical first).
# NOTE: finish_reason="length" (truncation) is handled by is_valid_end_of_turn
# in agent_endofturn_validate.py → recovery loop, not by retrying the same call.
_VALIDATORS = [
    _validate_tool_call_json,
    _validate_empty_reply,
    _validate_phantom_tool_calls,
]


def llm_validate(
    content: str,
    reasoning: str | None,
    tool_calls: list[dict],
    finish_reason: str | None = None,
) -> None:
    """Run validators in order; raise `InvalidReplyError` on first failure."""
    for validator in _VALIDATORS:
        reason = validator(content, reasoning, tool_calls, finish_reason)
        if reason is not None:
            warning(reason)
            raise InvalidReplyError(reason)


__all__ = [
    "InvalidReplyError",
    "_validate_tool_call_json",
    "_validate_empty_reply",
    "_validate_phantom_tool_calls",
    "_strip_phantoms",
    "_VALIDATORS",
    "llm_validate",
]
