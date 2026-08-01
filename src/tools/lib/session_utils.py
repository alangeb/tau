"""Shared utilities for tmux session management."""

from __future__ import annotations

import re
import subprocess
from typing import Dict

__all__ = ["session_exists", "validate_session", "strip_ansi", "capture_pane", "capture_delta",
           "is_prompt_line", "detect_prompt_return"]

# Track last capture line count per session for delta tracking
_last_capture_lines: Dict[str, int] = {}

# Comprehensive ANSI escape stripping (colors, OSC, character sets, etc.)
_ANSI_ESCAPE_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Multiple prompt patterns to handle various PS1 formats
_PROMPT_PATTERNS = [
    # user@host:path$ or user@host:path#
    re.compile(r"^[a-zA-Z0-9_.\-]+@[a-zA-Z0-9_.\-]+:[~a-zA-Z0-9_./\-]*[\$#]\s*$"),
    # Just $ or # (simple prompts)
    re.compile(r"^[\$#]\s*$"),
    # user@host$ or user@host#
    re.compile(r"^[a-zA-Z0-9_.\-]+@[a-zA-Z0-9_.\-]+[\$#]\s*$"),
]


def session_exists(name: str) -> bool:
    """Check if a tmux session with the given name exists."""
    result = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name}"],
        capture_output=True,
        text=True,
        start_new_session=True,
    )
    if result.returncode != 0:
        return False
    return name in result.stdout


def validate_session(session_name: str) -> str | None:
    """Return error message if session_name is invalid, else None."""
    if not session_name.startswith("tmux-agent-"):
        return "ERROR: Session name must start with 'tmux-agent-'"
    if not session_exists(session_name):
        return f"ERROR: Session '{session_name}' does not exist"
    return None


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def capture_pane(session_name: str, lines: int = 30) -> str:
    """Capture tmux pane and return last N lines.

    Captures full pane content including scrollback history, then slices
    to last N lines in Python.

    Args:
        session_name: tmux session name.
        lines: Number of lines to return from end.

    Returns:
        Last N lines of pane output, or empty string if capture fails.
    """
    # -S - captures from beginning of history buffer
    # -E - captures to end of history buffer
    result = subprocess.run(
        ["tmux", "capture-pane", "-p", "-S", "-", "-E", "-", "-t", session_name],
        capture_output=True,
        text=True,
        start_new_session=True,
    )
    if result.returncode != 0:
        return ""
    all_lines = strip_ansi(result.stdout).split("\n")
    # Update last capture tracking
    _last_capture_lines[session_name] = len(all_lines)
    last_lines = all_lines[-lines:] if len(all_lines) >= lines else all_lines
    return "\n".join(last_lines).strip() or ""


def strip_all_ansi(text: str) -> str:
    """Strip all ANSI escape sequences from text."""
    return _ANSI_ESCAPE_RE.sub("", text)


def is_prompt_line(line: str) -> bool:
    """Check if a line is a bash prompt.
    
    Handles colored prompts, custom PS1 formats, and common variations.
    
    Args:
        line: The line to check.
        
    Returns:
        True if the line appears to be a bash prompt.
    """
    stripped = strip_all_ansi(line.strip())
    return any(p.match(stripped) for p in _PROMPT_PATTERNS)


def detect_prompt_return(output: str, previous_output: str) -> bool:
    """Detect if bash prompt returned (process exited).

    Checks if the last line of output is a bash prompt and the previous
    output didn't end with a bash prompt (indicating a process was running).

    Args:
        output: Current output.
        previous_output: Previous output.

    Returns:
        True if bash prompt returned after a process was running.
    """
    if not output or not previous_output:
        return False

    current_lines = output.strip().split("\n")
    previous_lines = previous_output.strip().split("\n")

    # Get last non-empty line from current output
    current_last = ""
    for line in reversed(current_lines):
        if line.strip():
            current_last = line.strip()
            break

    # Get last non-empty line from previous output
    previous_last = ""
    for line in reversed(previous_lines):
        if line.strip():
            previous_last = line.strip()
            break

    # Check if current last line is a bash prompt
    if not is_prompt_line(current_last):
        return False

    # Check if previous last line was NOT a bash prompt (process was running)
    if not previous_last or is_prompt_line(previous_last):
        return False

    # Check if output changed (new lines added)
    return len(current_lines) > len(previous_lines)


def capture_delta(session_name: str) -> str:
    """Capture only new output since last capture.

    Returns lines that appeared after the previous capture call.
    On first call, returns all output (no baseline established).

    Args:
        session_name: tmux session name.

    Returns:
        New lines since last capture, or empty string if no new output.
    """
    result = subprocess.run(
        ["tmux", "capture-pane", "-p", "-S", "-", "-E", "-", "-t", session_name],
        capture_output=True,
        text=True,
        start_new_session=True,
    )
    if result.returncode != 0:
        return ""

    all_lines = strip_ansi(result.stdout).split("\n")
    current_count = len(all_lines)

    # Get previous baseline
    previous_count = _last_capture_lines.get(session_name, 0)

    # Update tracking
    _last_capture_lines[session_name] = current_count

    # Return only new lines
    if current_count > previous_count and previous_count > 0:
        new_lines = all_lines[previous_count:]
        return "\n".join(new_lines).strip() or ""
    elif previous_count == 0:
        # First call - return all output but don't establish baseline yet
        # (caller should call capture_pane first to establish baseline)
        return ""

    return ""
