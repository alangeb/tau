"""Delegate command — orchestrator mode for task delegation.

Enforces tool restrictions via ToolFilter at execution time. All tools are
still announced to the LLM (prefix cache preserved), but non-allowed tools
are blocked when called with a denied message.

## How Delegate Works

Delegate mode is an **orchestrator loop**: the agent plans and delegates work
via `fork` and `subagent` tools, but does NOT do work itself (no file edits,
no shell commands, no writes).

### Loop Mechanics

1. **First turn**: `invoke_with_tools(task + DELEGATE_INSTRUCTIONS)`
   - LLM plans and delegates subtasks
   - Returns when LLM ends turn (end_turn tool, ENDOFTURN sentinel, or budget)

2. **Continue loop**: While the LLM has NOT ended the turn, inject
   `"Continue TASK"` to prompt more delegation work.

3. **Exit condition**: The loop exits when `invoke_with_tools()` returns a
   response that does NOT start with `"Error:"`. This means the LLM has
   completed its work and ended the turn normally.

### Why Not Check `force_end_turn`?

The old code checked `while agent.force_end_turn is None`. This was WRONG
because `force_end_turn` is only set by external intervention (`+stop`
steering, loop escalation). It is NOT set by the normal EOT flow.

Result: If the LLM ended the turn normally, `force_end_turn` remained `None`,
and the loop kept injecting "Continue TASK" forever.

### Tool Restrictions

Delegate mode restricts tools to read/analysis + delegation only:
- **Allowed**: fork, subagent, glob, file_read, pyscan, grep, info, plan,
  skill, wc, head, ls, pygraph, pyanalyze, pycheck, end_turn
- **Blocked**: Everything else (file_write, bash, background_run, etc.)

The tool filter is applied at execution time. All tools are still announced
to the LLM (prefix cache preserved), but non-allowed tools are blocked when
called with a denied message.

### Design Notes

- The LLM is instructed to track progress itself and respond when done
- There is no iteration limit — the LLM decides when to stop
- The continue loop exists to handle cases where the LLM needs multiple
  turns to complete all delegation (e.g., delegating to multiple subagents)
"""

from __future__ import annotations

from agent_console import blank_line, echo, status
from agent_tool_filter import ToolFilter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_core import TauErgon

# ── Metadata ──

NAME = "delegate"
DESCRIPTION = "Enter orchestrator mode (plan & delegate via fork/subagent)"
subcommands = ()
help_text = "Usage: /delegate <task description>"

# Tools allowed in delegate mode — read/analysis + delegation only
_ALLOWED_DELEGATE_TOOLS = frozenset({
    # Delegation
    "fork", "subagent",
    # Read/analysis
    "glob", "file_read", "pyscan", "grep", "info", "plan", "skill",
    "wc", "head", "ls", "pygraph", "pyanalyze", "pycheck",
    # Turn control
    "end_turn",
})

DELEGATE_INSTRUCTIONS = (
    "You are in DELEGATE MODE. You are an orchestrator — you plan and delegate, "
    "you do NOT do work yourself.\n"
    "\n"
    "Rules:\n"
    "  1. Break the task into subtasks and delegate each via `fork` (needs full "
    "context) or `subagent` (isolated, blank-slate).\n"
    "  2. NEVER do work yourself — no file edits, no shell commands, no writes.\n"
    "  3. Your children (fork/subagent) have FULL tool access. You do not.\n"
    "  4. When all subtasks are done or abandoned: respond with a comprehensive summary.\n"
    "  5. Use read/analysis tools (glob, file_read, pyscan, grep) to understand "
    "the codebase before delegating.\n"
    "  6. There is no iteration limit — track progress yourself and respond when done.\n"
    "\n"
    "Begin delegating."
)


# ── Execution ──

def run(agent: TauErgon, args: list[str]) -> None:
    if not args or args[0] in ("help", "-h", "h"):
        echo("Usage: /delegate <task description>")
        return

    task = " ".join(args)
    blank_line()
    status(f"[DELEGATE MODE] Task: {task}")
    blank_line()

    # Enforce tool restrictions via ToolFilter at execution time.
    # All tools are still announced (prefix cache preserved), but non-allowed
    # tools are blocked when called with a denied message.
    original_filter = agent.tool_filter
    agent.tool_filter = ToolFilter(
        allowlist=_ALLOWED_DELEGATE_TOOLS,
        denied_message=(
            "Tool '{tool_name}' is not permitted in delegate mode. "
            "You are an orchestrator — plan and delegate, do not do work yourself. "
            "Available tools: {available_tools}. "
            "Use fork/subagent to delegate work."
        ),
    )
    try:
        agent.force_end_turn = None
        prompt = f"TASK: {task}\n\n{DELEGATE_INSTRUCTIONS}"
        result = agent.invoke_with_tools(prompt)

        # Continue loop: only keep injecting "Continue TASK" if the turn
        # was interrupted (result is None). invoke_with_tools() returns the
        # final response text when the LLM ends the turn normally (end_turn
        # tool, ENDOFTURN sentinel, or budget exhaustion). If result is a
        # string (normal or error), the LLM has ended the turn — stop.
        # If result is None, the turn was interrupted — try again.
        max_iterations = 10  # Safety limit to prevent infinite loops
        iteration = 0
        while result is None and iteration < max_iterations:
            iteration += 1
            result = agent.invoke_with_tools(
                f"Continue TASK.\n\n{DELEGATE_INSTRUCTIONS}"
            )
    finally:
        agent.force_end_turn = None
        agent.tool_filter = original_filter
