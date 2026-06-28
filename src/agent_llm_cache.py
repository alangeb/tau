"""Prefix cache tracker for LLM requests.

Estimates expected prefix cache hit rate by comparing consecutive request bodies.
Extracted from agent_llm.py.
"""

from __future__ import annotations

import json


class PrefixCacheTracker:
    """Track expected vs actual prefix cache hits by comparing request bodies.

    Warnings are always emitted (never suppressed):
    - Gap: expected - actual >= 20pp
    - Params: model or tools changed
    - Low expected: expected hit < 25%
    - Low actual: actual hit < 25%
    """

    _DIVERGENCE_CONTEXT_LEN = 15  # chars on each side of divergence point

    def __init__(self) -> None:
        self._last_request_body: bytes | None = None
        self._last_params_key: bytes | None = None
        self._prev_request_body: bytes | None = None
        self._prev_params_key: bytes | None = None

    def compute_expected_hit(self, body_bytes: bytes) -> tuple[float, str]:
        """Compute expected prefix cache hit rate from request body bytes.

        Compares current request body with the previous one to estimate
        what fraction of the context can be served from the prefix cache.

        Saves the previous body to ``_prev_request_body`` so ``diagnose_miss``
        can compare the current body against the one that was actually sent.

        Returns:
            (expected_hit_rate 0.0-1.0, reason_string)
        """
        try:
            body = json.loads(body_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return 0.0, "unparseable body"

        params_key = self._extract_params_key(body)

        if self._last_params_key is not None and params_key != self._last_params_key:
            changed = self._find_param_changes(self._last_params_key, params_key)
            self._prev_request_body = self._last_request_body
            self._prev_params_key = self._last_params_key
            self._last_params_key = params_key
            self._last_request_body = body_bytes
            return 0.0, f"params changed: {changed}"

        if self._last_request_body is None:
            # First call — no previous body to compare.
            # Store current body as _prev_request_body so diagnose_miss can use it
            # on the next call.
            self._prev_request_body = body_bytes
            self._prev_params_key = params_key
            self._last_params_key = params_key
            self._last_request_body = body_bytes
            return 0.0, "first call (no previous context)"

        # Save previous body and params for diagnosis BEFORE updating
        self._prev_request_body = self._last_request_body
        self._prev_params_key = self._last_params_key

        common = self._longest_common_prefix(self._last_request_body, body_bytes)
        total = len(body_bytes)
        expected = common / total if total > 0 else 0.0

        if expected < 0.25 and common < len(self._last_request_body):
            div_context = self._format_divergence(self._last_request_body, body_bytes, common)
            reason = f"prefix match: {common}/{total} bytes ({expected:.1%}) — {div_context}"
        else:
            reason = f"prefix match: {common}/{total} bytes ({expected:.1%})"

        self._last_params_key = params_key
        self._last_request_body = body_bytes
        return expected, reason

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def diagnose_miss(self, current_body_bytes: bytes) -> str:
        """Diagnose why a prefix cache miss may have occurred.

        Compares *current_body_bytes* against ``_prev_request_body`` (the body
        from the previous request that was actually sent to the LLM).

        Checks params stability, prefix match percentage, and body size delta.

        Args:
            current_body_bytes: The current request body bytes.

        Returns:
            Human-readable diagnosis string.
        """
        reasons: list[str] = []

        if self._prev_request_body is None:
            return "no previous request to compare"

        # Check params
        try:
            current_body = json.loads(current_body_bytes.decode("utf-8"))
            current_params = self._extract_params_key(current_body)
            if self._prev_params_key is not None and current_params != self._prev_params_key:
                changed = self._find_param_changes(self._prev_params_key, current_params)
                reasons.append(f"params changed: {changed}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            reasons.append("unparseable current body")

        # Prefix match — compare current against the PREVIOUS body
        prev_body = self._prev_request_body
        common = self._longest_common_prefix(prev_body, current_body_bytes)
        total = len(current_body_bytes)
        prev_total = len(prev_body)
        match_pct = (common / total * 100) if total > 0 else 0
        reasons.append(f"prefix match: {common}/{total} bytes ({match_pct:.1f}%)")

        # Size delta
        size_delta = total - prev_total
        if size_delta != 0:
            sign = "+" if size_delta > 0 else ""
            reasons.append(f"body size delta: {sign}{size_delta} bytes ({prev_total} -> {total})")

        # Divergence context
        if common < min(prev_total, total):
            div_ctx = self._format_divergence(prev_body, current_body_bytes, common)
            reasons.append(div_ctx)

        return "; ".join(reasons)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _format_divergence(self, old_body: bytes, new_body: bytes, divergence_pos: int) -> str:
        """Show ~15 chars around the divergence point in both bodies."""
        ctx = self._DIVERGENCE_CONTEXT_LEN
        old_snippet = old_body[max(0, divergence_pos - ctx):divergence_pos + ctx].decode("utf-8", errors="replace")
        new_snippet = new_body[max(0, divergence_pos - ctx):divergence_pos + ctx].decode("utf-8", errors="replace")
        return f"diverged@{divergence_pos}: '{old_snippet}' vs '{new_snippet}'"

    def _extract_params_key(self, body: dict) -> bytes:
        """Extract model+tools as a deterministic cache-invalidation key.

        Only 'model' and 'tools' invalidate prefix cache in major backends.
        Generation params (temperature, top_p, etc.) do not affect prefill KV cache.
        """
        params = {}
        if "model" in body:
            params["model"] = body["model"]
        if "tools" in body:
            params["tools"] = body["tools"]
        return json.dumps(params, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _find_param_changes(self, old_params_key: bytes, new_params_key: bytes) -> str:
        """Find which params changed between two parameter sets.

        Args:
            old_params_key: JSON-encoded params from the previous request.
            new_params_key: JSON-encoded params from the current request.
        """
        try:
            old = json.loads(old_params_key.decode("utf-8"))
            new = json.loads(new_params_key.decode("utf-8"))
            changed = [k for k in sorted(set(old.keys()) | set(new.keys())) if old.get(k) != new.get(k)]
            return ", ".join(changed) if changed else "unknown"
        except (json.JSONDecodeError, UnicodeDecodeError):
            return "unparseable"

    @staticmethod
    def _longest_common_prefix(a: bytes, b: bytes) -> int:
        """Return length of longest common byte prefix."""
        length = 0
        for x, y in zip(a, b):
            if x == y:
                length += 1
            else:
                break
        return length

    def reset(self) -> None:
        """Clear all stored state."""
        self._last_request_body = None
        self._last_params_key = None
        self._prev_request_body = None
        self._prev_params_key = None


__all__ = [
    "PrefixCacheTracker",
]
