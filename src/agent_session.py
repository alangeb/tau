"""Session lifecycle management for TauErgon.

Encapsulates session file paths, audit writer management, error burst
detection, token tracking, and utility functions that were previously
inline in the TauErgon god class.

Responsibilities:
- Session file path resolution (audit, context) with env overrides
- Audit writer management (delegates to agent_audit_writer)
- Error burst detection (via AgentSessionManager.has_error_burst)
- Token tracking (session-wide totals + per-turn snapshots + cache tracking)
- Utility functions for oversized output and failed API requests

Audit logging (AuditWriter, ErrorRateTracker, _classify_error) has been
extracted to agent_audit_writer.py for modularity. This module re-exports
them for backward compatibility.
"""

from __future__ import annotations

import json
import os
from datetime import datetime as dt
from pathlib import Path
from typing import Any

# Re-export audit writer components for backward compatibility.
# Direct imports should prefer agent_audit_writer.
from agent_audit_writer import (
    AuditWriter,
    ErrorRateTracker,
    _classify_error,
)

from agent_console import log_dir_error
from agent_audit_bridge import emit_console_warning, set_audit_writer
from agent_token_tracker import TokenTracker

__all__ = [
    "LOG_DIR",
    "SESSION_PREFIX",
    # Re-exported from agent_audit_writer (backward compatibility)
    "AuditWriter",
    "ErrorRateTracker",
    "_classify_error",
    # Defined here
    "AgentSessionManager",
    "write_oversized_output",
    "log_failed_api_request",
    "_get_log_filename_prefix",
]

# ── Directories ────────────────────────────────────────────────────────────────

_LOG_DIR_DEFAULT = Path.home() / ".local" / "tau" / "log"
LOG_DIR = Path(os.getenv("TAU_LOG_DIR", str(_LOG_DIR_DEFAULT)))

# Global session prefix — set ONCE by the root agent, inherited by all children.
# Never overwritten. Guarantees all session files share the same prefix.
SESSION_PREFIX: str | None = None


# ── Filename helpers ───────────────────────────────────────────────────────


def _get_log_filename_prefix() -> str:
    """Generate unique filename prefix: {ppid}_{YYYYMMDDHHMMSS}_{counter}."""
    ppid = os.getppid()
    dt_str = dt.now().strftime("%Y%m%d%H%M%S")
    counter = 1

    while True:
        prefix = f"{ppid}_{dt_str}_{counter}"
        ctx_file = LOG_DIR / f"{prefix}.context"
        if not ctx_file.exists():
            return prefix
        counter += 1


# ── Utility functions ────────────────────────────────────────────


def write_oversized_output(output: str, prefix: str | None) -> str | None:
    """Write oversized tool output to LOG_DIR/{prefix}.toolout.{NNN}.

    Returns the file path, or None if writing failed.
    """
    if prefix is None:
        return None
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        counter = 1
        while counter <= 1000:
            fname = f"{prefix}.toolout.{counter:03d}"
            filepath = LOG_DIR / fname
            if not filepath.exists():
                filepath.write_text(output, encoding="utf-8")
                return str(filepath)
            counter += 1
        emit_console_warning(
            f"Oversized output discarded — exhausted 1000 toolout slots for {prefix}. "
            "Consider cleaning old log files."
        )
        return None
    except Exception:
        return None


def log_failed_api_request(request_body: dict, log_file: Path | None = None) -> None:
    """Write failed LLM request body to a JSON file for debugging."""
    try:
        if log_file is not None:
            out_dir = log_file.parent
            prefix = log_file.stem
        elif SESSION_PREFIX is not None:
            out_dir = LOG_DIR
            prefix = SESSION_PREFIX
        else:
            out_dir = LOG_DIR
            prefix = f"{os.getppid()}_{dt.now().strftime('%Y%m%d%H%M%S')}"

        out_dir.mkdir(parents=True, exist_ok=True)
        filepath = out_dir / f"{prefix}.failed_request.json"

        record = {
            "timestamp": dt.now().isoformat(),
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "request": request_body,
        }
        filepath.write_text(
            json.dumps(record, indent=2, default=str), encoding="utf-8"
        )
    except Exception:
        pass


# ── AgentSessionManager ────────────────────────────────────────────


class AgentSessionManager:
    """Manages session lifecycle: file paths, audit writer, error detection,
    and token tracking.

    Extracted from TauErgon to reduce the god class. Provides a focused
    interface for session file management, audit logging, and token accounting.
    """

    def __init__(
        self,
        setup_files: bool = True,
        audit_file: Path | None = None,
        context_file: Path | None = None,
    ) -> None:
        """Initialise session manager.

        Args:
            setup_files: If True, ensure LOG_DIR exists and resolve file paths
                from the session prefix. Set to False when paths are provided
                explicitly (e.g., during tests).
            audit_file: Explicit audit file path (overrides env / prefix logic).
            context_file: Explicit context file path (overrides env / prefix logic).
        """
        self._audit_file = audit_file
        self._context_file = context_file
        self._audit_writer: AuditWriter | None = None
        self._tokens = TokenTracker()

        if setup_files:
            global SESSION_PREFIX
            try:
                LOG_DIR.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                log_dir_error(LOG_DIR, str(e))
                raise RuntimeError(f"Cannot create log directory {LOG_DIR}: {e}") from e

            # Resolve session prefix (global, set once by root agent).
            if SESSION_PREFIX is None:
                prefix = _get_log_filename_prefix()
                SESSION_PREFIX = prefix
            else:
                prefix = SESSION_PREFIX

            self._audit_file = LOG_DIR / f"{prefix}.audit"
            self._context_file = LOG_DIR / f"{prefix}.context"

            # Environment-variable overrides (checked after prefix resolution).
            if env_audit := os.getenv("TAU_AUDIT_LOG_FILE"):
                self._audit_file = Path(env_audit)
            if env_ctx := os.getenv("TOOL_CONTEXT_FILE"):
                self._context_file = Path(env_ctx)

            # Parent audit file inheritance (for fork unification).
            # TAU_PARENT_AUDIT_FILE takes highest priority — forks append to parent's file.
            parent_audit = os.getenv("TAU_PARENT_AUDIT_FILE")
            if parent_audit:
                self._audit_file = Path(parent_audit)

    # TokenTracker attributes delegated via __getattr__/__setattr__ (whitelist-based).
    _TOKEN_ATTRS = frozenset((
        "input_tokens", "output_tokens", "cached_tokens",
        "last_turn_input_tokens", "last_turn_output_tokens",
        "last_turn_cached_tokens", "last_exact_context_tokens",
        "cache_tracker",
        "record_call_stats", "clear_tokens", "reset_last_turn",
    ))

    def __getattr__(self, name: str) -> Any:
        """Delegate TokenTracker attributes to the internal tracker."""
        if name in self._TOKEN_ATTRS:
            return getattr(self._tokens, name)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        """Delegate TokenTracker attribute writes to the internal tracker."""
        if name in self._TOKEN_ATTRS:
            setattr(self._tokens, name, value)
        else:
            super().__setattr__(name, value)

    # ── File paths ──────────────────────────────────────────────────────────
    @property
    def audit_file(self) -> Path:
        """Path to the audit log file."""
        if self._audit_file is None:
            raise RuntimeError("Session files not initialised")
        return self._audit_file

    @audit_file.setter
    def audit_file(self, path: Path) -> None:
        self._audit_file = path

    @property
    def context_file(self) -> Path:
        """Path to the context file."""
        if self._context_file is None:
            raise RuntimeError("Session files not initialised")
        return self._context_file

    @context_file.setter
    def context_file(self, path: Path) -> None:
        self._context_file = path

    # ── Audit writer ────────────────────────────────────────────────────────

    def _create_audit_writer(self) -> AuditWriter:
        """Create, register, and return a new AuditWriter for the session."""
        initial_nesting = int(os.getenv("TAU_FORK_NESTING", "0"))
        writer = AuditWriter(self.audit_file, initial_nesting=initial_nesting)
        set_audit_writer(writer)
        return writer

    @property
    def audit_writer(self) -> AuditWriter:
        """Lazy-initialised AuditWriter for the session."""
        if self._audit_writer is None:
            self._audit_writer = self._create_audit_writer()
        return self._audit_writer

    def init_audit_writer(self) -> None:
        """Eagerly initialise the audit writer."""
        _ = self.audit_writer  # Triggers lazy initialisation in the property

    # ── Error burst detection ────────────────────────────────────────────────

    def has_error_burst(self) -> bool:
        """Return True if the audit writer's error tracker should alert.

        Delegates to ``AuditWriter.should_alert()`` — no more three-level
        private access into ``audit_writer._error_tracker``.
        """
        return self.audit_writer.should_alert()
