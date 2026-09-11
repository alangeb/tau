"""Manifests command — list manifests and show hierarchy.

Wraps the manifest_tree tool for CLI use. Supports tree view (default),
root filtering, and list mode.
"""

from __future__ import annotations

from agent_console import blank_line, echo, status
from tools import ToolContext
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_core import TauErgon

# ── Metadata ──

NAME = "manifests"
DESCRIPTION = "List manifests and show hierarchy"
subcommands = ()
help_text = "Usage: /manifests [--tree] [--root <path>] [--list]"


# ── Execution ──

def run(agent: TauErgon, args: list[str]) -> None:
    if not args or args[0] in ("help", "-h", "h"):
        echo(help_text)
        return

    # Parse flags
    root_filter = ""
    list_mode = False
    tree_mode = True  # default

    for arg in args:
        if arg == "--root":
            # Next arg is the root path
            idx = args.index(arg)
            if idx + 1 < len(args):
                root_filter = args[idx + 1]
        elif arg == "--list":
            list_mode = True
            tree_mode = False
        elif arg == "--tree":
            tree_mode = True

    blank_line()

    from tools.manifest_tree import run as manifest_tree_run
    from tools.manifest_tree import Args, _STATUS_ICONS
    from tools.lib.manifest import load_manifests
    from pathlib import Path

    if tree_mode:
        status("[MANIFESTS] Tree view")
        blank_line()

        result = manifest_tree_run(
            _ctx=ToolContext(agent=agent, tool_call_id=None),
            args=Args(root=root_filter) if root_filter else None,
        )
        echo(result)
    elif list_mode:
        status("[MANIFESTS] List view")
        blank_line()

        manifests_dir = Path.cwd() / ".tau" / "manifests"
        if not manifests_dir.is_dir():
            echo("No manifests found in .tau/manifests/")
            return

        entries = load_manifests(manifests_dir)
        if not entries:
            echo("No manifests found in .tau/manifests/")
            return

        for e in entries:
            icon = _STATUS_ICONS.get(e.status, "?")
            echo(f"  {icon} {e.filename}  [{e.status}]  title={e.title}  depth={e.depth}")
