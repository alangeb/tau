"""Audit bridge — breaks the circular dependency between console modules and agent_session.

This module provides a clean interface for console-to-audit bridging WITHOUT
creating circular imports. It contains NO imports from agent_console,
or agent_session, making the dependency graph acyclic.

Dependency graph (acyclic):
    agent_audit_bridge  (no deps on console/session)
    ↑                     ↑
    agent_console agent_session
    (facade imports bridge)   (imports bridge)
"""

from __future__ import annotations

from typing import Any, Callable

__all__ = [
    "set_audit_writer",
    "register_console_warning_callback",
    "emit_console_warning",
    "log_console_error",
    "log_console_warning",
    "log_console_info",
    "log_console_success",
    "log_context_add",
    "log_context_remove",
    "log_context_merge",
    "log_context_snapshot",
]


# ── Audit writer protocol ────────────────────────────────────────────────────
# We use a string-based protocol description instead of a formal Protocol class
# to avoid importing from agent_session (which would create the cycle).
#
# The audit writer object must support:
#   console_error(message: str) -> None
#   console_warning(message: str) -> None
#   console_info(message: str) -> None
#   console_success(message: str) -> None


# ── Global state ─────────────────────────────────────────────────────────────
# Single audit writer reference, shared across the process.
# Set once during AgentSessionManager initialization.
# Forks inherit via subprocess isolation (separate address spaces).
_audit_writer: Any = None

# Callback registered by agent_console.messages to emit console warnings without
# importing agent_session directly. This breaks the cycle.
#
# NOTE: agent_console.messages registers its warning() function at module load time.
# If emit_console_warning() is called before the callback is registered, the
# warning is silently dropped. This is acceptable: agent_console.messages is always
# imported early via agent_console during normal startup.
_console_warning_callback: Callable[[str], None] | None = None


# ── Core helpers ─────────────────────────────────────────────────────────────

def _call_audit_writer(method_name: str, *args: Any) -> None:
    """Call a method on the audit writer, silently catching exceptions.

    Shared implementation for all bridge functions. No-op if no writer is set.
    Audit failures must never suppress the caller's output.
    """
    global _audit_writer
    writer = _audit_writer
    if writer is not None:
        try:
            getattr(writer, method_name)(*args)
        except Exception:
            # Audit failure must never suppress console output.
            pass


def set_audit_writer(writer: Any) -> None:
    """Set the global audit writer reference for console-to-audit bridging.

    This allows console functions (error, warning) to log to audit
    without requiring a direct dependency on AuditWriter.

    Args:
        writer: An AuditWriter instance, or None to clear.
    """
    global _audit_writer
    _audit_writer = writer


def register_console_warning_callback(callback: Callable[[str], None]) -> None:
    """Register a callback for emitting console warnings.

    agent_session calls this to emit warnings without importing agent_session.
    agent_console.messages registers its warning() function here.

    Args:
        callback: A function that accepts a warning message string.
    """
    global _console_warning_callback
    _console_warning_callback = callback


def emit_console_warning(message: str) -> None:
    """Emit a console warning via the registered callback.

    No-op if no callback is registered (e.g., before agent_console.messages is loaded).
    Exceptions from the callback are caught to prevent audit/logging failures
    from breaking tool execution.
    """
    if _console_warning_callback is not None:
        try:
            _console_warning_callback(message)
        except Exception:
            # Callback failure must never break tool execution.
            pass


# ── Console logging ──────────────────────────────────────────────────────────
# Bridge functions for console output logging. Each delegates to
# _call_audit_writer with the appropriate method name.


def log_console_error(message: str) -> None:
    """Log a console error to the audit writer.

    Called by agent_console.messages.error() to bridge console output to audit.
    No-op if no writer is set.
    """
    _call_audit_writer("console_error", message)


def log_console_warning(message: str) -> None:
    """Log a console warning to the audit writer.

    Called by agent_console.messages.warning() to bridge console output to audit.
    No throttle — ALL warnings are logged (NEVER TRUNCATE principle).
    No-op if no writer is set.
    """
    _call_audit_writer("console_warning", message)


def log_console_info(message: str) -> None:
    """Log a console info message to the audit writer.

    Called by agent_console to bridge info output to audit.
    No-op if no writer is set.
    """
    _call_audit_writer("console_info", message)


def log_console_success(message: str) -> None:
    """Log a console success message to the audit writer.

    Called by agent_console to bridge success output to audit.
    No-op if no writer is set.
    """
    _call_audit_writer("console_success", message)


# ── Context logging ──────────────────────────────────────────────────────────
# Bridge functions for context modification logging. Each delegates to
# _call_audit_writer with the appropriate method name.


def log_context_add(count: int, total: int, bytes_total: int) -> None:
    """Log context messages added.

    Called by agent_context to log message additions.
    No-op if no writer is set.
    """
    _call_audit_writer("context_add", count, total, bytes_total)


def log_context_remove(count: int, total: int, bytes_total: int) -> None:
    """Log context messages removed.

    Called by agent_context to log message removals.
    No-op if no writer is set.
    """
    _call_audit_writer("context_remove", count, total, bytes_total)


def log_context_merge(source: str, target: str, count: int) -> None:
    """Log context messages merged.

    Called by agent_context to log message merges.
    No-op if no writer is set.
    """
    _call_audit_writer("context_merge", source, target, count)


def log_context_snapshot(total: int, bytes_total: int, max_tokens: int) -> None:
    """Log a context snapshot.

    Called by agent_context at key points (compression, turn boundaries).
    No-op if no writer is set.
    """
    _call_audit_writer("context_snapshot", total, bytes_total, max_tokens)