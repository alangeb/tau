from __future__ import annotations

from tools import ToolContext, ToolMetadata

import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_core import TauErgon


# ── Tool metadata ────────────────────────────────────────────────────────────

metadata = ToolMetadata(
    name="head",
    description="Display the first N lines of a file. Useful for quick previews of large files.",
    aliases_arg={"file_path": "path", "file": "path", "filename": "path"},
    max_size=32768,
    timeout=10,
)


# ── Args schema ──────────────────────────────────────────────────────────────

@dataclass
class Args:
    path: str = field(metadata={"description": "File path to read"})
    lines: int = field(default=10, metadata={"description": "Number of lines to read"})



# ── Execution ────────────────────────────────────────────────────────────────

def run(
    path: str, lines: int = 10,
    _ctx: ToolContext | None = None,
) -> str:
    agent = _ctx.agent if _ctx else None
    tool_call_id = _ctx.tool_call_id if _ctx else None
    try:
        result = subprocess.run(
            ["head", "-n", str(lines), path],
            capture_output=True,
            text=True,
            timeout=10,
            start_new_session=True,
        )
        if result.returncode == 0:
            return result.stdout
        return f"ERROR: {result.stderr.strip()}"

    except subprocess.TimeoutExpired:
        return "ERROR: head timed out after 10 seconds."
    except Exception as e:
        return f"ERROR: {e}"
