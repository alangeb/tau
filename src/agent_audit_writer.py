"""Audit writer and error tracking for TauErgon.

Extracted from agent_session.py to separate audit logging concerns from
session lifecycle management.

Responsibilities:
- Structured error categorization (_classify_error)
- Sliding-window error rate tracking (ErrorRateTracker)
- Buffered audit log writing (AuditWriter)

This module has NO dependency on agent_session.py, breaking the circular
dependency chain. It depends only on:
  - agent_console (for warning() display)
  - agent_version (lazy import for session_start)

# ============================================================================
# AUDIT LOGGING — NON-NEGOTIABLE DESIGN REQUIREMENTS
# ============================================================================
#
# The audit log is the ABSOLUTE SOURCE OF TRUTH for every agent session.
# It is the single, complete, immutable record of what happened.
#
# These requirements are MANDATORY and must NEVER be relaxed:
#
#   1. NEVER TRUNCATE — Tool outputs, user messages, assistant responses,
#      stack traces, system prompts, tool schemas: everything is logged in
#      full. No character limits, no byte limits, no line limits.
#
#   2. NEVER ROTATE — The audit file grows for the lifetime of the session.
#      No log rotation, no archival, no compression-on-write. A 100 MB file
#      is acceptable. A 1 GB file is acceptable. Disk space is cheap; data
#      loss is not.
#
#   3. NEVER REVERT — The audit log is append-only. Once written, a record
#      is immutable. Never overwrite, never delete, never "correct" past
#      entries. If something was wrong, log a new record describing the
#      correction — but never change what was already recorded.
#
#   4. AUDIT IS THE SOURCE OF TRUTH — All debugging, post-mortem analysis,
#      and LLM learning signals derive from the audit log. If it is incomplete
#      or inaccurate, everything downstream is compromised.
#
# We are AWARE and ACCEPT that audit files may grow very large. This is a
# deliberate trade-off: completeness over storage efficiency.
#
# ============================================================================
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime as dt
from pathlib import Path

from agent_audit_bridge import emit_console_warning

# ── EOT confirmation audit record types ────────────────────────────────────
# These were previously emitted as raw string literals to _emit().
# Defined as constants for type safety, discoverability, and consistency.
EOT_CONFIRM_SENTINEL = "EOT_CONFIRM_SENTINEL"
EOT_SELF_CONFIRMED = "EOT_SELF_CONFIRMED"
EOT_CONFIRM_REQUEST = "EOT_CONFIRM_REQUEST"
EOT_CONFIRM_ACCEPTED = "EOT_CONFIRM_ACCEPTED"

__all__ = [
    "_classify_error",
    "ErrorRateTracker",
    "AuditWriter",
    "EOT_CONFIRM_SENTINEL",
    "EOT_SELF_CONFIRMED",
    "EOT_CONFIRM_REQUEST",
    "EOT_CONFIRM_ACCEPTED",
]


# ── Error categorization ────────────────────────────────────────────────────

# Structured error categories for audit tracking and analysis.
# Each category groups related error types for meaningful reporting.
_ERROR_CATEGORIES = {
    "timeout": {"TimeoutError", "ToolTimeout"},
    "validation": {"ValidationError", "TypeError", "ValueError", "KeyError"},
    "connection": {"ConnectionError", "OSError", "URLError"},
    "file_operation": {"FileNotFoundError", "PermissionError", "IsADirectoryError"},
    "tool_not_found": {"AttributeError"},  # e.g., tool function missing
    "argument_error": {"IndexError"},
    "execution": {"RuntimeError", "RecursionError", "MemoryError"},
    "api": {"APIError", "APITimeoutError", "APIConnectionError", "RateLimitError", "UnauthorizedError", "BadRequestError"},
}

# Reverse lookup: error_type -> category
_ERROR_TYPE_TO_CATEGORY: dict[str, str] = {}
for _cat, _types in _ERROR_CATEGORIES.items():
    for _t in _types:
        _ERROR_TYPE_TO_CATEGORY[_t] = _cat


def _classify_error(error_type: str) -> str:
    """Classify an error type string into a structured category.

    Returns the category name, or 'unknown' if the error type has no
    matching category.  Matches are done by exact name and by substring
    (e.g. 'ToolTimeout' -> 'timeout', 'FileNotFoundError' -> 'file_operation').
    """
    # Exact match first
    cat = _ERROR_TYPE_TO_CATEGORY.get(error_type)
    if cat:
        return cat

    # Substring match for compound names like 'some.ModuleError'
    for _cat, _types in _ERROR_CATEGORIES.items():
        for _t in _types:
            if _t in error_type:
                return _cat

    return "unknown"


# ── ErrorRateTracker ──────────────────────────────────────────────────────


class ErrorRateTracker:
    """Thread-safe error rate tracker with sliding window calculations.

    Timestamps are NEVER cleared — they persist for accurate rate calculation.
    Burst detection uses a cooldown mechanism to avoid re-triggering.
    """

    def __init__(
        self,
        window_size: float = 300.0,
        alert_threshold: float = 10.0,
        burst_window: float = 5.0,
        burst_threshold: int = 3,
    ):
        self.window_size = window_size
        self.alert_threshold = alert_threshold
        self.burst_window = burst_window
        self.burst_threshold = burst_threshold
        self._lock = threading.Lock()

        self._error_timestamps: list[float] = []
        self._tool_error_timestamps: dict[str, list[float]] = {}
        self._error_type_counts: dict[str, int] = {}
        # Per-category tracking for structured error analysis
        self._category_counts: dict[str, int] = {}
        self._last_alert_time: float = 0.0
        self._alert_cooldown: float = 60.0
        # Cooldown for burst detection: after a burst fires, wait this long
        # before allowing another burst to be detected. Prevents re-triggering
        # WITHOUT clearing timestamps (which would corrupt rate calculation).
        self._last_burst_time: float = 0.0
        self._burst_cooldown: float = 30.0

    def record_error(self, tool_name: str | None, error_type: str) -> bool:
        """Record an error. Returns True if an alert should be triggered."""
        now = time.time()
        category = _classify_error(error_type)

        with self._lock:
            self._error_timestamps.append(now)
            if tool_name:
                self._tool_error_timestamps.setdefault(tool_name, []).append(now)

            self._error_type_counts[error_type] = (
                self._error_type_counts.get(error_type, 0) + 1
            )

            # Track category counts
            self._category_counts[category] = (
                self._category_counts.get(category, 0) + 1
            )

            self._check_burst(now)
            return self._check_alert(now)

    def _check_burst(self, now: float) -> None:
        """Check if recent errors constitute a burst (must hold self._lock).

        Uses cooldown to avoid re-triggering — NEVER clears timestamps.
        """
        # Cooldown: don't re-trigger if we just detected a burst.
        if now - self._last_burst_time < self._burst_cooldown:
            return

        window_start = now - self.burst_window
        recent = [t for t in self._error_timestamps if t >= window_start]

        if len(recent) >= self.burst_threshold:
            self._last_burst_time = now

    def _check_alert(self, now: float) -> bool:
        """Check if error rate exceeds alert threshold (must hold self._lock)."""
        if now - self._last_alert_time < self._alert_cooldown:
            return False

        recent = [t for t in self._error_timestamps if t >= now - self.window_size]
        error_rate = len(recent) / max(self.window_size / 60.0, 0.001)

        if error_rate >= self.alert_threshold:
            self._last_alert_time = now
            return True

        return False

    def get_error_rate(self, tool_name: str | None = None) -> float:
        """Calculate error rate (errors/minute) over sliding window."""
        now = time.time()
        cutoff = now - self.window_size

        with self._lock:
            timestamps = (
                self._tool_error_timestamps.get(tool_name, [])
                if tool_name
                else self._error_timestamps
            )
            recent = [t for t in timestamps if t >= cutoff]
            return len(recent) / max(self.window_size / 60.0, 0.001)

    def should_alert(self) -> bool:
        """Check if current error rate exceeds alert threshold."""
        return self.get_error_rate() >= self.alert_threshold


# ── AuditWriter ───────────────────────────────────────────────────────────


class AuditWriter:
    """Buffered writer for structured audit log records.

    Writes structured text records to an audit file with synchronous
    flush-at-turn-boundaries. No truncation — audit is never truncated.

    Format: [TIMESTAMP] RECORD_TYPE nesting=N field1=value1 field2=value2
            | continuation_line
    """

    def __init__(self, audit_file: Path, pid: int | None = None, initial_nesting: int = 0):
        self._file = audit_file
        self._pid = pid or os.getppid()
        self._buffer: list[str] = []

        # Single source of truth for error rates — AuditWriter delegates here.
        self._error_tracker = ErrorRateTracker()
        self._lock = threading.Lock()
        self._nesting_level = initial_nesting

        try:
            audit_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # --- Timestamp & buffering -------------------------------------------------------

    def _ts(self) -> str:
        return dt.now().isoformat(timespec="milliseconds")

    def _enqueue(self, line: str) -> None:
        self._buffer.append(line)

    def _enqueue_indented(self, label: str, text: str) -> None:
        """Enqueue a labeled block of indented lines."""
        self._enqueue(f"  | {label}:\n")
        for line in text.split("\n"):
            self._enqueue(f"  |   {line}\n")

    def _flush(self) -> None:
        if not self._buffer:
            return
        data = "".join(self._buffer)
        try:
            with open(self._file, "a", encoding="utf-8") as f:
                f.write(data)
            self._buffer.clear()  # Only clear after successful write
        except Exception as e:
            # Graceful degradation: log to stderr, retain buffer for retry.
            sys.stderr.write(
                f"CRITICAL: Audit write failed: {e}\n"
                f"File: {self._file}\n"
                f"Buffer: {len(data)} bytes (retained for retry)\n"
            )
            sys.stderr.flush()
            # Buffer is NOT cleared — next flush will retry the write.

    def _emit(self, record_type: str, fields: str, continuations: list[str] | None = None) -> None:
        ts = self._ts()
        nesting = f"nesting={self._nesting_level}"
        # Format: [TS] RECORD_TYPE nesting=N fields
        if fields:
            header = f"[{ts}] {record_type} {nesting} {fields}\n"
        else:
            header = f"[{ts}] {record_type} {nesting}\n"
        self._enqueue(header)
        if continuations:
            for line in continuations:
                self._enqueue(f"  | {line}\n")

    # --- Session lifecycle ---------------------------------------------------------

    def session_start(
        self,
        model: str,
        tool_count: int,
        cwd: str,
        system_prompt: str,
        tool_schema: list[dict],
    ) -> None:
        # Import here to avoid circular dependencies
        from agent_version import get_version_info
        version_info = get_version_info()
        fields = f"version={version_info['version']} branch={version_info['branch']!r} hash={version_info['hash']!r} pid={self._pid} model={model!r} tools={tool_count} cwd={cwd!r}"
        self._emit("SESSION_START", fields)
        self._enqueue_indented("system_prompt", system_prompt)

        schema_json = json.dumps(tool_schema, default=str)
        self._enqueue_indented("tool_schema", schema_json)

    # --- Message logging -----------------------------------------------------------

    def user(self, content: str | list) -> None:
        """Log a user message (backward compatible — no truncation)."""
        if isinstance(content, list):
            image_count = sum(1 for p in content if p.get("type") == "image_url")
            text_parts = [p.get("text", "") for p in content if p.get("type") == "text"]
            audit_text = f"[{image_count} image(s), {len(text_parts)} text block(s)]"
            if text_parts:
                # NO TRUNCATION — log full content
                audit_text += ": " + text_parts[0]
            self._emit("USER", "", [audit_text])
        else:
            self._emit("USER", "", [content])

    def assistant(self, content: str, reasoning: str | None = None) -> None:
        """Log an assistant response (backward compatible)."""
        parts = [f"content_len={len(content)}"]
        if reasoning:
            parts.append(f"reasoning_len={len(reasoning)}")
        fields = " ".join(parts)
        self._emit("ASSISTANT", fields)
        if content:
            self._enqueue_indented("content", content)
        if reasoning:
            self._enqueue_indented("reasoning", reasoning)

    # --- Tool logging ---------------------------------------------------------------

    def tool_call(
        self,
        call_id: str,
        original_name: str,
        original_args: dict,
        final_name: str,
        final_args: dict,
        fixes: list[str],
    ) -> None:
        orig_json = json.dumps(original_args, default=str)
        final_json = json.dumps(final_args, default=str)
        fixes_str = "; ".join(fixes) if fixes else "none"
        fields = f"id={call_id} original_name={original_name!r} final_name={final_name!r} fixes={fixes_str}"
        self._emit("TOOL_CALL", fields)
        self._enqueue(f"  | original_args: {orig_json}\n")
        self._enqueue(f"  | final_args: {final_json}\n")

    def tool_result(
        self,
        call_id: str,
        status: str,
        duration_ms: float,
        output: str,
        output_bytes: int,
        tool_name: str | None = None,
    ) -> None:
        parts = [f"id={call_id} status={status} duration_ms={duration_ms:.0f} bytes={output_bytes}"]
        if tool_name is not None:
            parts.append(f"tool={tool_name!r}")
        fields = " ".join(parts)
        self._emit("TOOL_RESULT", fields)
        self._enqueue_indented("output", output)

    def tool_error(
        self,
        call_id: str,
        error_type: str,
        error_message: str,
        stack_trace: str | None = None,
        tool_name: str | None = None,
        tool_args: dict | None = None,
        parent_chain: list[str] | None = None,
        nesting_level: int = 0,
        session_duration_s: float | None = None,
        concurrent_ops: int | None = None,
        duration_ms: float | None = None,
    ) -> None:
        """Log tool execution error with optional stack trace and rich context."""
        category = _classify_error(error_type)
        parts = [f"id={call_id} error_type={error_type} category={category}"]
        if tool_name is not None:
            parts.append(f"tool={tool_name!r}")
        if tool_args is not None:
            parts.append(f"args={json.dumps(tool_args, default=str)}")
        if parent_chain:
            parts.append(f"chain={'→'.join(parent_chain)}")
        if nesting_level:
            parts.append(f"nesting={nesting_level}")
        if session_duration_s is not None:
            parts.append(f"session_dur={session_duration_s:.1f}s")
        if duration_ms is not None:
            parts.append(f"tool_dur={duration_ms:.0f}ms")
        if concurrent_ops is not None:
            parts.append(f"concurrent={concurrent_ops}")
        fields = " ".join(parts)

        self._emit("TOOL_ERROR", fields)
        self._enqueue(f"  | error_message: {error_message}\n")
        if stack_trace:
            self._enqueue_indented("stack_trace", stack_trace)

        # Delegate to ErrorRateTracker — it handles burst detection internally.
        self._error_tracker.record_error(tool_name=tool_name, error_type=error_type)

    def tool_blocked(
        self,
        call_id: str,
        tool_name: str,
        available_str: str,
    ) -> None:
        """Log a blocked tool invocation (expected, not an error)."""
        fields = (
            f"id={call_id} tool={tool_name!r} "
            f"available={available_str}"
        )
        self._emit("TOOL_BLOCKED", fields)

    # --- Error tracking (delegates to ErrorRateTracker) -----------------------------

    def should_alert(self) -> bool:
        """Return True if the error rate exceeds the alert threshold."""
        return self._error_tracker.should_alert()

    # --- Subagent / fork logging ---------------------------------------------------

    def fork_start(self, task: str) -> None:
        with self._lock:
            self._nesting_level += 1
            self._emit("FORK_START", f"task={task!r}")
            self._flush()  # Ensure FORK_START is on disk before fork writes

    def fork_end(self, duration_s: float) -> None:
        with self._lock:
            if self._nesting_level <= 0:
                emit_console_warning("Audit nesting underflow: fork_end() without matching fork_start()")
            self._nesting_level = max(0, self._nesting_level - 1)
            self._emit("FORK_END", f"duration_s={duration_s:.1f}")

    def subagent_start(self, task: str) -> None:
        with self._lock:
            self._nesting_level += 1
            self._emit("SUBAGENT_START", f"task={task!r}")
            self._flush()  # Ensure SUBAGENT_START is on disk before subagent writes

    def subagent_end(self, duration_s: float) -> None:
        with self._lock:
            if self._nesting_level <= 0:
                emit_console_warning("Audit nesting underflow: subagent_end() without matching subagent_start()")
            self._nesting_level = max(0, self._nesting_level - 1)
            self._emit("SUBAGENT_END", f"duration_s={duration_s:.1f}")

    # --- Misc logging ------------------------------------------------------------

    def tool_truncated(
        self,
        call_id: str,
        tool_name: str,
        output_bytes: int,
        max_size: int,
        file_path: str,
    ) -> None:
        fields = (
            f"id={call_id} tool={tool_name!r} output_bytes={output_bytes} "
            f"max_size={max_size} file={file_path!r}"
        )
        self._emit("TOOL_TRUNCATED", fields)

    # --- Compression logging (backward compatible) ---------------------------------

    def compress_start(self, step_name: str, bytes_before: int, msgs_before: int) -> None:
        """Log the start of a compression pipeline step."""
        fields = f"step={step_name!r} bytes_before={bytes_before} msgs_before={msgs_before}"
        self._emit("COMPRESS_STEP_START", fields)

    def compress_action(self, step_name: str, action_type: str, details: str) -> None:
        """Log an individual compression action within a step."""
        fields = f"step={step_name!r} action={action_type} details={details}"
        self._emit("COMPRESS_ACTION", fields)

    def compress_step_end(self, step_name: str, bytes_after: int, msgs_after: int, status: str) -> None:
        """Log the end of a compression pipeline step."""
        fields = f"step={step_name!r} bytes_after={bytes_after} msgs_after={msgs_after} status={status!r}"
        self._emit("COMPRESS_STEP_END", fields)

    # --- Compression logging (pipeline) -------------------------------------------

    def compress_pipeline_start(self, original_size: int, target_size: int, compression_factor: float, last_known_tokens: int | None) -> None:
        """Log the start of the compression pipeline with metadata."""
        fields = f"original_size={original_size} target_size={target_size} compression_factor={compression_factor} last_known_tokens={last_known_tokens}"
        self._emit("COMPRESS_PIPELINE_START", fields)

    def compress_pipeline_end(self, final_size: int, algorithms_used: list[str], bytes_saved: int) -> None:
        """Log the end of the compression pipeline with final metrics."""
        fields = f"final_size={final_size} algorithms_used={algorithms_used!r} bytes_saved={bytes_saved}"
        self._emit("COMPRESS_PIPELINE_END", fields)

    # --- Context logging ------------------------------------------------------------

    def context_add(self, count: int, total: int, bytes_total: int) -> None:
        """Log context messages added."""
        fields = f"count={count} total={total} bytes_total={bytes_total}"
        self._emit("CONTEXT_ADD", fields)

    def context_remove(self, count: int, total: int, bytes_total: int) -> None:
        """Log context messages removed."""
        fields = f"count={count} total={total} bytes_total={bytes_total}"
        self._emit("CONTEXT_REMOVE", fields)

    def context_merge(self, source: str, target: str, count: int) -> None:
        """Log context messages merged."""
        fields = f"source={source!r} target={target!r} count={count}"
        self._emit("CONTEXT_MERGE", fields)

    def context_snapshot(self, total: int, bytes_total: int, max_tokens: int) -> None:
        """Log a context snapshot."""
        fields = f"total={total} bytes_total={bytes_total} max_tokens={max_tokens}"
        self._emit("CONTEXT_SNAPSHOT", fields)

    # --- Console-to-audit bridging (INTERNAL — use agent_audit_bridge only) --------
    # These methods are NOT part of the public API. They are called exclusively
    # through agent_audit_bridge explicit functions (console_error, console_warning,
    # console_info, console_success), which provide exception handling and
    # guard against writer being None. Direct calls bypass this safety mechanism.

    def _console_error(self, message: str) -> None:
        """Log a console error message to audit. INTERNAL — use agent_audit_bridge."""
        self._emit("CONSOLE_ERROR", "", [message])

    def _console_warning(self, message: str) -> None:
        """Log a console warning message to audit. INTERNAL — use agent_audit_bridge."""
        self._emit("CONSOLE_WARNING", "", [message])

    def _console_info(self, message: str) -> None:
        """Log a console info message to audit. INTERNAL — use agent_audit_bridge."""
        self._emit("CONSOLE_INFO", "", [message])

    def _console_success(self, message: str) -> None:
        """Log a console success message to audit. INTERNAL — use agent_audit_bridge."""
        self._emit("CONSOLE_SUCCESS", "", [message])

    # --- EOT confirmation audit events ---

    def eot_confirm_sentinel(self, response_preview: str, stripped: bool) -> None:
        """Log that the LLM confirmed EOT with the sentinel during a confirmation round."""
        self._emit(
            EOT_CONFIRM_SENTINEL,
            f"response={response_preview!r} stripped={stripped}"
        )

    def eot_self_confirmed(self, response_preview: str, stripped: bool) -> None:
        """Log that the LLM self-confirmed EOT (sentinel in a non-confirmation round)."""
        self._emit(
            EOT_SELF_CONFIRMED,
            f"response={response_preview!r} stripped={stripped}"
        )

    def eot_confirm_request(self, stack_depth: int, held_preview: str) -> None:
        """Log that an EOT confirmation request was injected into the context."""
        self._emit(
            EOT_CONFIRM_REQUEST,
            f"stack_depth={stack_depth} held_preview={held_preview!r}"
        )

    def eot_confirm_accepted(self, source: str, stack_depth: int, final_len: int) -> None:
        """Log that an EOT confirmation was accepted and the turn was closed."""
        self._emit(
            EOT_CONFIRM_ACCEPTED,
            f"source={source} stack_depth={stack_depth} final_len={final_len}"
        )

    # --- Flush / close ------------------------------------------------------------

    def flush(self) -> None:
        self._flush()

    def close(self) -> None:
        self._flush()

