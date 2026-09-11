"""Orchestrate command — goal-driven delegation with accountability.

Wraps the orchestrate tool for CLI use. Supports simple mode (auto-create
manifest with goal as criteria), resume mode, and default fork+executor flow.
"""

from __future__ import annotations

from agent_console import blank_line, echo, status
from tools import ToolContext
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_core import TauErgon

# ── Metadata ──

NAME = "orchestrate"
DESCRIPTION = "Goal-driven delegation with accountability"
subcommands = ()
help_text = "Usage: /orchestrate <goal> [--simple] [--resume <path>]"


# ── Execution ──

def run(agent: TauErgon, args: list[str]) -> None:
    if not args or args[0] in ("help", "-h", "h"):
        echo(help_text)
        return

    # Parse flags and goal
    goal_parts: list[str] = []
    simple = False
    resume_path = ""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--simple":
            simple = True
        elif arg == "--resume":
            i += 1
            if i < len(args):
                resume_path = args[i]
        else:
            goal_parts.append(arg)
        i += 1

    if not goal_parts:
        echo("Error: goal is required")
        echo(help_text)
        return

    goal = " ".join(goal_parts)
    blank_line()
    status(f"[ORCHESTRATE] Goal: {goal}")
    blank_line()

    from tools.orchestrate import run as orchestrate_run

    if resume_path:
        result = orchestrate_run(
            goal=goal,
            resume=resume_path,
            _ctx=ToolContext(agent=agent, tool_call_id=None),
        )
    elif simple:
        # Simple mode: create a manifest with the goal as criteria, then
        # resume execution on it.
        from tools.manifest_create import run as manifest_create_run

        create_result = manifest_create_run(
            goal=goal,
            title=goal,
            success_criteria=goal,
            _ctx=ToolContext(agent=agent, tool_call_id=None),
        )
        echo(f"Created manifest: {create_result}")
        result = orchestrate_run(
            goal=goal,
            resume=create_result,
            _ctx=ToolContext(agent=agent, tool_call_id=None),
        )
    else:
        result = orchestrate_run(
            goal=goal,
            _ctx=ToolContext(agent=agent, tool_call_id=None),
        )

    if result:
        echo(result)
