"""HTTP client for OpenAI-compatible LLM APIs.

Stdlib-only client (urllib + json) with cache tracking. Extracted from agent_llm.py.
"""

from __future__ import annotations

import json
import os
import random as _random
import socket
import time
from typing import Any

import urllib.error
import urllib.request

from agent_console import warning
from agent_llm_cache import PrefixCacheTracker
from agent_llm_models import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    BadRequestError,
    Choice,
    Function,
    Message,
    RateLimitError,
    Response,
    ToolCall,
    UnauthorizedError,
    Usage,
    CONTEXT_OVERFLOW_INDICATORS,
)


def _is_context_overflow(error_str: str) -> bool:
    """Return True if *error_str* contains a known context overflow indicator."""
    return any(indicator in error_str for indicator in CONTEXT_OVERFLOW_INDICATORS)


# ---------------------------------------------------------------------------
# Retry backoff — configurable, jittered, interruptible
# ---------------------------------------------------------------------------

class RetryBackoff:
    """Configurable backoff with exponential growth, jitter, and interruptibility.

    Usage:
        backoff = RetryBackoff(base=5, max_wait=300, jitter=0.3)
        for attempt in range(max_retries):
            try:
                ...
            except TransientError:
                if attempt == max_retries - 1:
                    raise
                backoff.wait(attempt)
    """

    def __init__(
        self,
        base: float = 5.0,
        max_wait: float = 300.0,
        jitter: float = 0.3,
        multiplier: float = 2.0,
    ):
        self.base = base
        self.max_wait = max_wait
        self.jitter = jitter
        self.multiplier = multiplier

    def wait(self, attempt: int) -> None:
        """Sleep for the backoff interval, interruptible by SIGINT."""
        raw = min(self.base * (self.multiplier ** attempt), self.max_wait)
        # Apply jitter: ±jitter fraction
        if self.jitter > 0:
            swing = raw * self.jitter
            wait = raw + _random.uniform(-swing, swing)
        else:
            wait = raw
        wait = max(0.1, wait)  # Floor at 100ms

        # Interruptible sleep — check for SIGINT every second
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(remaining, 1.0))

    def next_wait(self, attempt: int) -> float:
        """Return the wait time for *attempt* without sleeping."""
        raw = min(self.base * (self.multiplier ** attempt), self.max_wait)
        if self.jitter > 0:
            swing = raw * self.jitter
            return max(0.1, raw + _random.uniform(-swing, swing))
        return max(0.1, raw)


# ---------------------------------------------------------------------------
# Chat completion wrapper (provides chat.completions.create() interface)
# ---------------------------------------------------------------------------

class SimpleChatCompletion:
    """Wrapper providing chat.completions.create() interface."""

    def __init__(self, client: "SimpleOpenAIClient"):
        self._client = client

    def create(self, **kwargs) -> Any:
        return self._client.chat_completions_create(**kwargs)


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

# HTTP error code → exception mapping
_HTTP_ERROR_MAP = {
    400: BadRequestError,
    401: UnauthorizedError,
    429: RateLimitError,
}


class SimpleOpenAIClient:
    """Drop-in replacement for OpenAI client using stdlib only (urllib + json)."""

    @staticmethod
    def _safe_get(data: dict, *keys, expected_type=None, default=None):
        """Traverse nested dict keys with optional type validation."""
        if not isinstance(data, dict):
            return default
        current = data
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        if expected_type is not None:
            if current is None and type(None) in (
                expected_type if isinstance(expected_type, tuple) else (expected_type,)
            ):
                return current
            if not isinstance(current, expected_type):
                return default
        return current

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: int = 300,
        cache_tracker: PrefixCacheTracker | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("API_KEY", "")
        self.timeout = timeout
        self._cache_tracker = cache_tracker
        self.chat = type("Chat", (), {"completions": SimpleChatCompletion(self)})()

    def chat_completions_create(self, **kwargs) -> Any:
        url = f"{self.base_url}/chat/completions"
        data = json.dumps(kwargs, sort_keys=True).encode("utf-8")

        # Log full request body + audit one-liner for debugging/reproduction
        try:
            import agent_session as _sess
            from datetime import datetime as _dt

            log_dir = getattr(_sess, "LOG_DIR", None)
            prefix = getattr(_sess, "SESSION_PREFIX", None)
            if log_dir and prefix:
                # (1) Full request body → {prefix}.lr.json (for full reproduction)
                lr_file = log_dir / f"{prefix}.lr.json"
                lr_body = {
                    "url": url,
                    "timeout": self.timeout,
                    "kwargs": kwargs,
                }
                lr_file.write_text(
                    json.dumps(lr_body, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

                # (2) Audit one-liner → {prefix}.audit (params only, no context)
                audit_file = log_dir / f"{prefix}.audit"
                params = {k: kwargs[k] for k in (
                    "model", "max_tokens", "temperature", "top_p", "top_k",
                    "min_p", "presence_penalty", "frequency_penalty",
                    "repetition_penalty", "repeat_penalty", "seed",
                ) if k in kwargs}
                if "chat_template_kwargs" in kwargs:
                    params["chat_template_kwargs"] = kwargs["chat_template_kwargs"]
                if "extra_body" in kwargs:
                    params["extra_body"] = kwargs["extra_body"]
                params_str = " ".join(
                    f"{k}={json.dumps(v)}" for k, v in sorted(params.items())
                )
                ts = _dt.now().isoformat()
                with open(audit_file, "a", encoding="utf-8") as af:
                    af.write(f"[{ts}] LLM_CALL {params_str}\n")
        except Exception:
            pass  # Don't let logging failures break the request

        tracker = self._cache_tracker
        expected_hit, hit_reason = 0.0, "no-tracker"
        if tracker is not None:
            expected_hit, hit_reason = tracker.compute_expected_hit(data)

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                wrapped = self._wrap_response(result)
                self._report_cache_hit(wrapped, expected_hit, hit_reason, data)
                return wrapped

        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except (OSError, ValueError):
                pass

            exc_class = _HTTP_ERROR_MAP.get(e.code, APIError)
            raise exc_class(f"{exc_class.__name__}: {error_body}") from e

        except urllib.error.URLError as e:
            if self._is_timeout(e):
                raise APITimeoutError("Request timed out") from e
            if self._is_connection_refused(e):
                raise APIConnectionError(f"Connection refused: {e}") from e
            raise APIError(f"Request failed: {e}") from e

    @staticmethod
    def _is_timeout(e: urllib.error.URLError) -> bool:
        """Check if a URLError represents a timeout."""
        exc_str = str(e).lower()
        reason_str = str(getattr(e, "reason", "")).lower()
        return (
            "timeout" in exc_str
            or "timed out" in exc_str
            or "timeout" in reason_str
            or "timed out" in reason_str
            or isinstance(getattr(e, "reason", None), socket.timeout)
        )

    @staticmethod
    def _is_connection_refused(e: urllib.error.URLError) -> bool:
        """Check if a URLError represents a connection refusal (endpoint unreachable)."""
        reason = getattr(e, "reason", None)
        if isinstance(reason, (ConnectionRefusedError, socket.error)):
            return True
        reason_str = str(reason).lower()
        return (
            "connection refused" in reason_str
            or "errno 111" in reason_str
            or "errno 61" in reason_str  # macOS connection refused
        )

    def _report_cache_hit(
        self, response: Any, expected_hit: float, hit_reason: str, body_bytes: bytes
    ) -> None:
        """Warn on cache hit anomalies (warnings are always emitted).

        Passes *body_bytes* to ``diagnose_miss`` so it can compare the current
        request body against the previous one (``_prev_request_body``).
        """
        try:
            usage = getattr(response, "usage", None)
            if not usage:
                return
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            pt_details = getattr(usage, "prompt_tokens_details", None)
            cached_tokens = 0
            if pt_details and isinstance(pt_details, dict):
                cached_tokens = pt_details.get("cached_tokens", 0) or 0
            if prompt_tokens == 0:
                return
            actual_hit = cached_tokens / prompt_tokens

            gap = expected_hit - actual_hit
            if gap >= 0.20:
                warning(
                    f":: cache: expected {expected_hit:.0%} -> actual {actual_hit:.0%} "
                    f"(gap {gap:.0%}, prefix cache MISS)"
                )
                # Diagnose miss with divergence context
                tracker = self._cache_tracker
                if tracker is not None:
                    diag = tracker.diagnose_miss(body_bytes)
                    warning(f":: cache diag: {diag}")
            if "params changed" in hit_reason:
                warning(f":: cache: invalidated — {hit_reason}")
            if expected_hit < 0.25:
                warning(f":: cache: low expected {expected_hit:.0%} ({hit_reason})")
            if actual_hit < 0.25:
                warning(f":: cache: low actual {actual_hit:.0%} (cache underperforming)")
        except Exception:
            pass

    def _wrap_response(self, data: dict) -> Any:
        """Wrap raw API response dict into structured Response object."""
        if not isinstance(data, dict):
            return Response(choices=[], usage=Usage())

        choices = [self._wrap_choice(cd) for cd in self._safe_get(data, "choices", expected_type=list, default=[]) if isinstance(cd, dict)]

        usage_data = self._safe_get(data, "usage", expected_type=dict, default={})
        usage = Usage(
            prompt_tokens=self._safe_get(usage_data, "prompt_tokens", expected_type=int, default=0),
            completion_tokens=self._safe_get(usage_data, "completion_tokens", expected_type=int, default=0),
            total_tokens=self._safe_get(usage_data, "total_tokens", expected_type=int, default=0),
            prompt_tokens_details=self._safe_get(usage_data, "prompt_tokens_details", expected_type=dict, default=None),
        )

        return Response(
            choices=choices,
            usage=usage,
            id=self._safe_get(data, "id", expected_type=str),
            model=self._safe_get(data, "model", expected_type=str),
            created=self._safe_get(data, "created", expected_type=int),
        )

    def _wrap_choice(self, choice_data: dict) -> Choice:
        """Wrap a single choice dict into a Choice object."""
        message_data = self._safe_get(choice_data, "message", expected_type=dict, default={})
        tool_calls = [self._wrap_tool_call(tc) for tc in self._safe_get(message_data, "tool_calls", expected_type=list, default=[]) if isinstance(tc, dict)]

        reasoning_content = (
            self._safe_get(message_data, "reasoning", expected_type=str)
            or self._safe_get(message_data, "reasoning_content", expected_type=str)
        )

        return Choice(
            message=Message(
                content=self._safe_get(message_data, "content", expected_type=str),
                reasoning_content=reasoning_content,
                tool_calls=tool_calls,
                role=self._safe_get(message_data, "role", expected_type=str, default="assistant"),
            ),
            finish_reason=self._safe_get(choice_data, "finish_reason", expected_type=str),
            index=self._safe_get(choice_data, "index", expected_type=int, default=0),
        )

    def _wrap_tool_call(self, tc_data: dict) -> ToolCall:
        """Wrap a single tool call dict into a ToolCall object."""
        func_data = self._safe_get(tc_data, "function", expected_type=dict, default={})
        func_obj = Function(
            name=self._safe_get(func_data, "name", expected_type=str),
            arguments=self._safe_get(func_data, "arguments", expected_type=str),
        )
        return ToolCall(
            id=self._safe_get(tc_data, "id", expected_type=str),
            function=func_obj,
            type=self._safe_get(tc_data, "type", expected_type=str, default="function"),
        )


__all__ = [
    "_is_context_overflow",
    "RetryBackoff",
    "SimpleChatCompletion",
    "SimpleOpenAIClient",
    "_HTTP_ERROR_MAP",
]
