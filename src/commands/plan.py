"""Plan command — direct interface to the plan tool."""

from __future__ import annotations

from agent_console import echo, error
from tools import ToolContext
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_core import TauErgon

# ── Metadata ──
NAME = "plan"
DESCRIPTION = "Manage tasks: status, clear, create, add, complete, block, unblock, progress, update, delete"
ALIASES_CMD = ["task"]
subcommands = ("status", "clear", "create", "add", "complete", "block", "unblock", "next", "progress", "update", "delete")
help_text = """Usage: /plan <action> [args...]
Actions:
  status          Show plan status
  clear           Clear all tasks
  create          Create a new plan
  add <desc> [pri] Add a task (priority=low|medium|high)
  complete <id>   Mark task complete
  block <id> [reason] Block a task
  unblock <id>    Unblock a task
  next            Show next actionable task
  progress        Show completion percentage
  update <id>     Update a task
  delete <id>     Delete a task"""

_VALID_ACTIONS = {"status", "clear", "create", "add", "complete", "block", "unblock", "next", "progress", "update", "delete"}


# ── Execution ──
def run(agent: TauErgon, args: list[str]) -> None:
    if not args or args[0] in ("help", "-h", "h"):
        echo(
            "Usage: /plan <action> [args...]\n"
            "Actions:\n"
            "  status\n"
            "  clear\n"
            "  create\n"
            "  add <description> [priority=low|medium|high]\n"
            "  complete <task_id> [notes=...]\n"
            "  block <task_id> [blocker_reason=...]\n"
            "  unblock <task_id>\n"
            "  next\n"
            "  progress\n"
            "  update <task_id> [description=...]\n"
            "  delete <task_id>"
        )
        return

    action = args[0].lower()
    if action not in _VALID_ACTIONS:
        error(
            f"Unknown action: {action}. Valid: {', '.join(sorted(_VALID_ACTIONS))}"
        )
        return

    kwargs: dict[str, object] = {"action": action}

    positional: list[str] = []
    # Rejoin arguments that are part of a quoted value (e.g., description="Test task")
    # The shell splits on spaces, so we need to rejoin fragments that share quotes.
    raw_args: list[str] = []
    remaining = list(args[1:])
    i = 0
    while i < len(remaining):
        arg = remaining[i]
        # Check if this arg starts a quoted value (key="... or key='...)
        if "=" in arg:
            key, partial = arg.split("=", 1)
            quote_char = partial[0] if partial else ""
            if quote_char in ('"', "'"):
                # Start of a quoted value — collect until closing quote
                collected = partial
                j = i + 1
                while j < len(remaining) and not collected.endswith(quote_char):
                    collected = collected + " " + remaining[j]
                    j += 1
                raw_args.append(key + "=" + collected)
                i = j  # Skip past collected tokens
                continue
        raw_args.append(arg)
        i += 1

    for arg in raw_args:
        if "=" in arg:
            key, value = arg.split("=", 1)
            # Strip surrounding quotes from value
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            kwargs[key] = value
        else:
            positional.append(arg)

    if positional:
        if action == "add" and "description" not in kwargs:
            kwargs["description"] = " ".join(positional)
        elif "task_id" not in kwargs:
            kwargs["task_id"] = positional[0]

    from tools.plan import run as plan_run

    result = plan_run(_ctx=ToolContext(agent=agent, tool_call_id=None), **kwargs)
    if result:
        echo(result)
