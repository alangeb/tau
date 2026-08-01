"""Run a command in a background tmux session and wait for completion.

Convenience tool that combines session creation, command execution, and
waiting for completion. Returns the output when the command finishes.
"""

from __future__ import annotations

import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field

from tools import ToolMetadata, ToolContext
from .lib.session_utils import capture_pane, detect_prompt_return

# ── Tool metadata ──
metadata = ToolMetadata(
    name="background_run",
    description=(
        "Run a command in a background tmux session and wait for completion. "
        "Convenience tool combining session creation, command execution, and waiting. "
        "Returns output when the command finishes (prompt detected, keywords matched, "
        "idle timeout, or hard timeout). Use for simple background tasks. "
        "For advanced control (interactive input, custom polling), use background_new + "
        "background_exec + background_wait instead."
    ),
    aliases_cmd=["run_background_run"],
    max_size=131072,
    timeout=3600,
)

# Default history limit for new sessions (lines)
_DEFAULT_HISTORY_LIMIT = 5000


# ── Args schema ──
@dataclass
class Args:
    command: str = field(
        metadata={"description": "Command to execute in background"}
    )
    timeout: float = field(
        default=300.0,
        metadata={
            "description": (
                "Max seconds to wait for command completion. "
                "Defaults to 300 (5 minutes)."
            )
        },
    )
    idle_seconds: float = field(
        default=30.0,
        metadata={
            "description": (
                "Return early if no output for this many seconds. "
                "Defaults to 30."
            )
        },
    )
    keywords: str = field(
        default="",
        metadata={
            "description": (
                "Regex pattern to match against output. "
                "Returns immediately when matched. "
                "Default: empty (wait for prompt or timeout)."
            )
        }
    )
    session_name: str = field(
        default="",
        metadata={"description": "Session name (auto-generated if empty)"}
    )
    capture_lines: int = field(
        default=30,
        metadata={"description": "Number of output lines to return (default: 30)"}
    )


# ── Execution ──
def run(
    command: str, timeout: float = 300.0, idle_seconds: float = 30.0,
    keywords: str = "", session_name: str = "", capture_lines: int = 30,
    _ctx: ToolContext | None = None,
) -> str:
    """Run a command in background and wait for completion."""
    if not session_name:
        session_name = f"tmux-agent-{uuid.uuid4().hex[:8]}"

    # Create session
    try:
        result = subprocess.run(
            ["tmux", "new-session", "-d", "-s", session_name],
            capture_output=True,
            text=True,
            start_new_session=True,
        )
        if result.returncode != 0:
            return f"ERROR: Failed to create session '{session_name}': {result.stderr.strip()}"

        # Set per-session history limit
        subprocess.run(
            ["tmux", "set-option", "-t", session_name, "history-limit", str(_DEFAULT_HISTORY_LIMIT)],
            capture_output=True,
            text=True,
            start_new_session=True,
        )
    except Exception as e:
        return f"ERROR: Failed to create session: {e}"

    # Send command
    try:
        subprocess.run(
            ["tmux", "send-keys", "-t", session_name, command, "C-m"],
            capture_output=True,
            text=True,
            start_new_session=True,
        )
    except Exception as e:
        # Cleanup session on error
        subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True)
        return f"ERROR: Failed to send command: {e}"

    # Wait for completion (reuse shared prompt detection)
    # Compile keyword regex if provided
    keyword_pattern = None
    if keywords:
        try:
            keyword_pattern = re.compile(keywords, re.IGNORECASE)
        except re.error:
            return f"ERROR: Invalid regex pattern: {keywords}"

    last_output = ""
    last_output_time = time.time()
    start_time = time.time()
    poll_interval = 1

    while True:
        elapsed = time.time() - start_time

        # Hard timeout
        if elapsed >= timeout:
            output = capture_pane(session_name, max(capture_lines, 100))
            lines = output.strip().split("\n")[-capture_lines:] if output else []
            return f"TIMEOUT: Max wait {timeout:.0f}s reached\nOutput:\n" + "\n".join(lines)

        # Check if session is still alive
        alive_result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True,
            start_new_session=True,
        )
        if alive_result.returncode != 0 or session_name not in alive_result.stdout:
            return f"SESSION DEAD: Session '{session_name}' no longer exists after {elapsed:.0f}s\nLast output:\n{last_output}"

        # Capture current output
        current_output = capture_pane(session_name, max(capture_lines, 100))

        # Check for keyword match
        if keyword_pattern and keyword_pattern.search(current_output):
            lines = current_output.strip().split("\n")[-capture_lines:] if current_output else []
            return f"KEYWORD MATCH: '{keywords}' found after {elapsed:.0f}s\nOutput:\n" + "\n".join(lines)

        # Check for prompt return (process exited)
        if last_output and detect_prompt_return(current_output, last_output):
            lines = current_output.strip().split("\n")[-capture_lines:] if current_output else []
            return f"COMPLETED: Command finished after {elapsed:.0f}s\nOutput:\n" + "\n".join(lines)

        # Check for idle
        if current_output != last_output:
            last_output = current_output
            last_output_time = time.time()

        idle_time = time.time() - last_output_time
        if idle_time >= idle_seconds and last_output:
            lines = last_output.strip().split("\n")[-capture_lines:] if last_output else []
            return f"IDLE: No output for {idle_time:.0f}s (threshold: {idle_seconds:.0f}s)\nOutput:\n" + "\n".join(lines)

        time.sleep(poll_interval)
