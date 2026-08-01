"""Console-to-audit bridging for TauErgon.

This module provides the audit logging bridge that connects console output
to the audit log. It uses a global audit writer reference (set by
agent_session.AgentSessionManager) and a lock to prevent recursive calls.

Dependency graph (acyclic):
    agent_audit_bridge  (no deps on console/session)
    ↑                     ↑
    agent_console.audit   agent_session
    (imports bridge)      (imports bridge)

The _log_audit function is the primary interface. It is called by:
  - agent_console.messages (_ConsoleMessage.__call__ when audit=True)
  - agent_console.display (context validation/recovery display functions)
"""

from __future__ import annotations

import threading
from typing import Callable

__all__ = ["_log_audit"]

# Thread-safe recursion guard for _log_audit.
# Prevents audit → console → audit infinite loops.
_log_audit_lock = threading.Lock()

# Dispatch table mapping internal levels to bridge functions.
# Lazy-imported on first use to avoid circular imports at module load time.
_AUDIT_LEVEL_METHODS: dict[str, Callable] | None = None


def _get_audit_level_methods() -> dict[str, Callable]:
    """Build the level → bridge-function-name dispatch table (cached)."""
    global _AUDIT_LEVEL_METHODS
    if _AUDIT_LEVEL_METHODS is None:
        from agent_audit_bridge import (  # noqa: F811 — intentional lazy import
            log_console_error,
            log_console_info,
            log_console_success,
            log_console_warning,
        )
        _AUDIT_LEVEL_METHODS = {
            "error": log_console_error,
            "warning": log_console_warning,
            "info": log_console_info,
            "success": log_console_success,
        }
    return _AUDIT_LEVEL_METHODS


def _log_audit(level: str, message: str) -> None:
    """Bridge console output to audit log.

    Calls the global audit writer if available. No-op if audit is not initialized
    or if the writer fails (audit must never break console output).
    Unknown levels are silently ignored.
    Uses a lock to prevent audit → console → audit recursion.

    Args:
        level: Log level ("error", "warning", "info", "success").
        message: Message to log to audit.
    """
    if not _log_audit_lock.acquire(blocking=False):
        return  # Already in progress — prevent recursion
    try:
        handler = _get_audit_level_methods().get(level)
        if handler is not None:
            handler(message)
    finally:
        _log_audit_lock.release()
