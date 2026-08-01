from __future__ import annotations

from tools import ToolMetadata, ToolContext

import subprocess
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_core import TauErgon

# ── Tool metadata ──
metadata = ToolMetadata(
    name="background_new",
    description=(
        "Create a new tmux session for background processes. Auto-generates name if not provided. "
        "IMPORTANT: Before using background_* tools, load the skill first: skill('background')."
    ),
    aliases_cmd=["run_background_new", "background"],
    max_size=4096,
)

# Default history limit for new sessions (lines)
_DEFAULT_HISTORY_LIMIT = 5000


# ── Args schema ──
@dataclass
class Args:
    command: str = field(
        default="", metadata={"description": "Command to run in the session"}
    )
    session_name: str = field(
        default="", metadata={"description": "Session name (auto-generated if empty)"}
    )



# ── Execution ──
def run(
    command: str = "", session_name: str = "",
    _ctx: ToolContext | None = None,
) -> str:
    """Create a new tmux session for background processes."""
    agent = _ctx.agent if _ctx else None
    tool_call_id = _ctx.tool_call_id if _ctx else None
    if not session_name:
        session_name = f"tmux-agent-{uuid.uuid4().hex[:8]}"

    try:
        cmd = ["tmux", "new-session", "-d", "-s", session_name]
        if command:
            cmd.extend(["-c", command])

        result = subprocess.run(cmd, capture_output=True, text=True, start_new_session=True)
        if result.returncode != 0:
            return f"ERROR: Failed to create session '{session_name}': {result.stderr.strip()}"

        # Set per-session history limit (don't affect global tmux config)
        subprocess.run(
            ["tmux", "set-option", "-t", session_name, "history-limit", str(_DEFAULT_HISTORY_LIMIT)],
            capture_output=True,
            text=True,
            start_new_session=True,
        )

        return session_name
    except Exception as e:
        return f"ERROR: Failed to create session: {e}"
