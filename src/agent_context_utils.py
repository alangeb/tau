"""Shared context-file utilities for TauErgon.

Centralises functions that operate on context JSON files and the LOG_DIR
directory, eliminating duplication across ``agent_input``, ``agent_project``,
and ``agent_a2a``.

Public API
----------
- :func:`format_age` — human-readable age string from seconds
- :func:`get_all_context_files` — sorted list of context files in LOG_DIR
- :func:`read_context_metadata` — (msg_count, last_user) for display
- :func:`read_context_metadata_for_a2a` — (metadata_dict, message_count)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from agent_session import LOG_DIR

# Base pattern for context-file naming convention: {ppid}_{YYYYMMDDHHMMSS}_{N}
# Exported so other modules can derive their own compiled regexes.
_CONTEXT_FILE_PATTERN = r"\d+_\d+_\d+\.context"
_CONTEXT_FILE_RE = re.compile(r"^" + _CONTEXT_FILE_PATTERN + "$")

# Pattern with capture group for extracting the PID (first field).
# Used by agent_a2a.py to parse session PIDs from context filenames.
_CONTEXT_FILE_CAPTURE_RE = re.compile(r"^(" + r"\d+" + r")_\d+_\d+\.context$")


# ── Helpers ────────────────────────────────────────────────────────────────


def format_age(seconds: float) -> str:
    """Format a duration in seconds into a human-readable string.

    Examples: ``"42s ago"``, ``"5m ago"``, ``"3h ago"``, ``"2d ago"``.
    """
    if seconds < 60:
        return f"{int(seconds)}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{int(minutes)}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{int(hours)}h ago"
    days = hours // 24
    return f"{int(days)}d ago"


def _is_valid_path(path: Path) -> bool:
    """Check if path exists and is not a broken symlink."""
    try:
        if not path.exists():
            return False
        if path.is_symlink() and not path.resolve().exists():
            return False
        return True
    except OSError:
        return False


def get_all_context_files() -> list[Path]:
    """Get all context files in LOG_DIR, sorted newest first.

    Uses the session registry if available, falling back to scanning
    LOG_DIR directly. The registry enables archived sessions to be
    included and provides a single source of truth for file locations.

    Filters out broken symlinks.
    """
    try:
        from agent_session_registry import get_registry
        files = get_registry().get_context_files(include_archived=True)
        return [f for f in files if _is_valid_path(f)]
    except Exception:
        pass

    # Fallback: scan LOG_DIR directly
    ctx_files = [
        f for f in LOG_DIR.glob("*.context")
        if _CONTEXT_FILE_RE.match(f.name) and _is_valid_path(f)
    ]
    return sorted(ctx_files, key=lambda f: f.stat().st_mtime if _is_valid_path(f) else 0, reverse=True)


# ── Context-file readers ───────────────────────────────────────────────────

def _extract_last_user(data: list) -> str:
    """Extract a short preview of the last user message from *data*."""
    for msg in reversed(data):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                image_count = sum(
                    1
                    for p in content
                    if isinstance(p, dict) and p.get("type") == "image_url"
                )
                text_parts = [
                    p.get("text", "")
                    for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                result = f"[{image_count} image(s)]"
                if text_parts:
                    t = text_parts[0]
                    if len(t) > 80:
                        t = t[:77] + "..."
                    result += ": " + t
                return result
            elif isinstance(content, str):
                if len(content) > 80:
                    return content[:77] + "..."
                return content
    return ""


def read_context_metadata(context_file: Path) -> tuple[int, str]:
    """Read message count and last user message from a context JSON file.

    Handles both the legacy bare-array format (just a list of messages)
    and the TAU_005 metadata-wrapped format::

        {"metadata": {...}, "messages": [...]}

    Returns ``(msg_count, last_user)``.  On any read error returns ``(0, "")``.
    """
    try:
        with open(context_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return (0, "")

    if isinstance(data, dict) and "messages" in data:
        # New format with metadata — extract messages list
        messages = data.get("messages")
        if not isinstance(messages, list):
            return (0, "")
        msg_count = len(messages)
        last_user = _extract_last_user(messages)
        return (msg_count, last_user)
    if isinstance(data, list):
        # Legacy bare-array format
        msg_count = len(data)
        last_user = _extract_last_user(data)
        return (msg_count, last_user)

    return (0, "")


def read_context_metadata_for_a2a(context_file: Path) -> tuple[dict, int]:
    """Read a context file for A2A session metadata.

    Handles both the legacy bare-array format (just a list of messages)
    and the TAU_005 metadata-wrapped format::

        {"metadata": {...}, "messages": [...]}

    Returns ``(metadata_dict, message_count)``.
    Missing or unreadable files yield an empty metadata dict and a
    message count of 0.
    """
    try:
        with open(context_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return {}, 0

    if isinstance(data, dict) and "messages" in data:
        return data.get("metadata") or {}, len(data.get("messages") or [])
    if isinstance(data, list):
        return {}, len(data)
    return {}, 0


__all__ = [
    "_CONTEXT_FILE_PATTERN",
    "_CONTEXT_FILE_CAPTURE_RE",
    "format_age",
    "get_all_context_files",
    "read_context_metadata",
    "read_context_metadata_for_a2a",
]
