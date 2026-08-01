from __future__ import annotations

from tools import ToolMetadata, ToolContext

import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_core import TauErgon

# ── Tool metadata ──
metadata = ToolMetadata(
    name="background_ls",
    description="List active tmux sessions (agent sessions only by default).",
    aliases_cmd=["run_background_ls"],
    max_size=4096,
)


# ── Args schema ──
@dataclass
class Args:
    all_sessions: bool = field(
        default=False,
        metadata={
            "description": "List all sessions (True) or only agent sessions (False)"
        },
    )



# ── Execution ──
def run(
    all_sessions: bool = False,
    _ctx: ToolContext | None = None,
) -> str:
    """List active tmux sessions."""
    agent = _ctx.agent if _ctx else None
    tool_call_id = _ctx.tool_call_id if _ctx else None
    try:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True,
            start_new_session=True,
        )
        if result.returncode != 0:
            return f"ERROR: Failed to list sessions: {result.stderr.strip()}"

        sessions = [line.strip() for line in result.stdout.split("\n") if line.strip()]
        if not all_sessions:
            sessions = [s for s in sessions if s.startswith("tmux-agent-")]

        if not sessions:
            label = "tmux sessions" if all_sessions else "active tmux sessions"
            return f"No {label} found"
        return "\n".join(sessions)
    except Exception as e:
        return f"ERROR: Failed to list sessions: {e}"
