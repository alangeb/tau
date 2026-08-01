from __future__ import annotations

from tools import ToolMetadata, ToolContext

import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .lib.session_utils import validate_session

if TYPE_CHECKING:
    from agent_core import TauErgon

# ── Tool metadata ──
metadata = ToolMetadata(
    name="background_send_keys",
    description="Send keystrokes to a tmux session without execution. Use C-m to send Enter.",
    aliases_cmd=["run_background_send_keys"],
    max_size=2048,
)


# ── Args schema ──
@dataclass
class Args:
    session_name: str = field(
        metadata={"description": "Session name (required, must start with tmux-agent-)"}
    )
    text: str = field(metadata={"description": "Text/keystrokes to send"})



# ── Execution ──
def run(session_name: str, text: str, _ctx: ToolContext | None = None) -> str:
    """Send keystrokes to a tmux session without execution."""
    agent = _ctx.agent if _ctx else None
    tool_call_id = _ctx.tool_call_id if _ctx else None
    if err := validate_session(session_name):
        return err
    if not text:
        return "ERROR: text cannot be empty"

    try:
        result = subprocess.run(
            ["tmux", "send-keys", "-t", session_name, text],
            capture_output=True,
            text=True,
            start_new_session=True,
        )
        if result.returncode == 0:
            return f"Sent '{text}' to session '{session_name}'"
        return f"ERROR: Failed to send keys: {result.stderr.strip()}"
    except Exception as e:
        return f"ERROR: Failed to send keys: {e}"
