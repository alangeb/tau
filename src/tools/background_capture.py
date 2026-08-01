from __future__ import annotations

from tools import ToolMetadata, ToolContext

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .lib.session_utils import validate_session, capture_pane

if TYPE_CHECKING:
    from agent_core import TauErgon

# ── Tool metadata ──
metadata = ToolMetadata(
    name="background_capture",
    description="Capture tmux pane output with scrollback history.",
    aliases_cmd=["run_background_capture"],
    max_size=131072,
)


# ── Args schema ──
@dataclass
class Args:
    session_name: str = field(
        metadata={"description": "Session name (required, must start with tmux-agent-)"}
    )
    lines: int = field(
        default=30, metadata={"description": "Number of lines to show from end"}
    )


# ── Execution ──
def run(
    session_name: str, lines: int = 10,
    _ctx: ToolContext | None = None,
) -> str:
    """Show last N lines from tmux pane output."""
    agent = _ctx.agent if _ctx else None
    tool_call_id = _ctx.tool_call_id if _ctx else None
    if err := validate_session(session_name):
        return err
    if lines < 0:
        return "ERROR: lines must be non-negative"
    if lines == 0:
        return ""

    return capture_pane(session_name, lines) or "No output captured"
