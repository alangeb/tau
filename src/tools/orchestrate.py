"""Orchestrate tool — goal-driven delegation with accountability.

Spawns a fork to prepare a manifest + context, then runs an executor loop
that delegates subtasks via subagent/fork with tool restrictions enforced.

## How Orchestrate Works

Orchestrate mode is a **goal-driven delegation loop**: the agent prepares a
manifest (via fork), then executes subtasks (via executor) with strict tool
restrictions and manifest-based accountability.

### Flow

1. **Fork phase**: Spawn a fork with FORK_INSTRUCTIONS to investigate the
   codebase and create a manifest + .ctx file.

2. **Extract manifest path**: Parse fork output to find the manifest path.

3. **Validate manifest**: Ensure the manifest has required sections.

4. **Executor phase**: Run the executor loop with tool restrictions,
   delegating subtasks and tracking progress via manifest_update.

5. **Block exit**: The executor loop continues until the manifest is
   marked complete/failed or max iterations reached.

### Resume Mode

If a manifest path is provided via `resume`, skip the fork phase and
jump directly to the executor. Auto-resume detects one executing manifest
matching the goal.

### Tool Restrictions

Orchestrate mode restricts tools to delegation + manifest management +
read/analysis:
- **Allowed**: fork, subagent, orchestrate, manifest_*, read/analysis tools
- **Blocked**: Everything else (file_write, bash, background_run, etc.)

The tool filter is applied at execution time. All tools are still announced
to the LLM (prefix cache preserved), but non-allowed tools are blocked when
called with a denied message.

### Design Notes

- The fork does the investigation and manifest creation
- The executor delegates work and tracks progress
- Retries are tracked per-subtask via manifest_update state
- The executor blocks exit until manifest is complete/failed
"""

from __future__ import annotations

from tools import ToolContext, ToolMetadata
from tools.lib.manifest import (
    load_manifests,
    read_manifest_frontmatter,
)

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_core import TauErgon

__all__ = ["Args", "run"]

# ── Tool metadata ─────────────────────────────────────────────────

metadata = ToolMetadata(
    name="orchestrate",
    description=(
        "Goal-driven delegation with accountability. Spawns a fork to "
        "prepare a manifest + context, then runs an executor loop that "
        "delegates subtasks via subagent/fork. Supports resume mode and "
        "auto-resume. Enforces tool restrictions. Blocks exit until "
        "manifest is complete/failed."
    ),
    timeout=86400,
    max_size=262144,
)

# ── Allowed tools ─────────────────────────────────────────────────

_ALLOWED_ORCHESTRATE_TOOLS = frozenset({
    # Delegation
    "fork", "subagent",
    # Orchestration (recursive)
    "orchestrate",
    # Manifest management
    "manifest_create", "manifest_update", "manifest_tree",
    # Read/analysis
    "glob", "file_read", "pyscan", "grep", "info", "skill",
    "wc", "head", "ls", "pygraph", "pyanalyze", "pycheck",
    # Turn control
    "end_turn",
})

# ── Instructions templates ────────────────────────────────────────

FORK_INSTRUCTIONS = (
    "You are in ORCHESTRATE PREPARE MODE. Your job is to investigate the "
    "codebase and create a manifest + context file for goal-driven delegation.\n"
    "\n"
    "Steps:\n"
    "  1. Investigate the codebase using pyscan, pygraph, glob, file_read, "
    "and grep to understand the relevant code and structure.\n"
    "  2. Create a manifest using the `manifest_create` tool with:\n"
    "     - goal: The goal to achieve\n"
    "     - title: A descriptive title\n"
    "     - success_criteria: Concrete, verifiable criteria (each with a "
    "Verify command in backticks)\n"
    "     - subtasks: Specific subtasks to achieve the goal\n"
    "  3. Create a .ctx file using `file_write` at the same location as the "
    "manifest (same stem, .ctx extension) containing:\n"
    "     - Key findings from your investigation\n"
    "     - Relevant file paths and their purposes\n"
    "     - Important constraints or requirements\n"
    "     - Any decisions made during planning\n"
    "  4. Return ONLY the manifest path (e.g., .tau/manifests/manifest-YYYYMMDDHHMMSS.md).\n"
    "\n"
    "IMPORTANT: The manifest path MUST be in your final response text so the "
    "orchestrator can extract it.\n"
    "\n"
    "Begin investigating and creating the manifest.\n"
)

EXECUTOR_INSTRUCTIONS = (
    "You are in ORCHESTRATE EXECUTOR MODE. You are responsible for executing "
    "the tasks defined in a manifest file by delegating work via subagent/fork.\n"
    "\n"
    "Rules:\n"
    "  1. Read the manifest file and its .ctx context file.\n"
    "  2. Update manifest status to 'executing' using `manifest_update`.\n"
    "  3. For each subtask, delegate via `subagent` (isolated, blank-slate) "
    "or `fork` (needs full context) with clear instructions.\n"
    "  4. After each subtask completes, verify the result and update the "
    "manifest using `manifest_update` to mark progress.\n"
    "  5. Handle retries: if a subtask fails, check retry_budget and retry "
    "with adjusted instructions.\n"
    "  6. Use read/analysis tools (glob, file_read, pyscan, grep) to verify "
    "results.\n"
    "  7. When ALL subtasks are complete (or all retries exhausted):\n"
    "     - Update manifest status to 'complete' (or 'failed' if critical "
    "tasks failed)\n"
    "     - Provide a comprehensive summary\n"
    "  8. DO NOT exit until the manifest is marked complete or failed.\n"
    "  9. You can recursively use `orchestrate` for sub-goals.\n"
    "\n"
    "Manifest: {manifest_path}\n"
    "Context: {ctx_path}\n"
    "Max depth: {max_depth}\n"
    "Retry budget: {retry_budget}\n"
    "\n"
    "Begin executing.\n"
)

# ── Args schema ───────────────────────────────────────────────────

@dataclass
class Args:
    goal: str
    title: str = ""
    max_depth: int = 3
    retry_budget: int = 2
    resume: str = ""  # manifest path to resume

# ── Helper functions ──────────────────────────────────────────────

def _extract_manifest_path(text: str) -> str | None:
    """Find manifest path in fork output.

    Looks for paths matching .tau/manifests/manifest-*.md or
    absolute paths containing manifest-*.md.
    """
    # Try absolute paths with common prefixes (longer match wins)
    abs_match = re.search(
        r"(/(?:home|tmp|root|opt|usr|srv|var|mnt|media)[^\s]*manifest-\d{14}\.md)",
        text
    )
    if abs_match:
        return abs_match.group(1)

    # Try relative paths (.tau/manifests/...)
    rel_match = re.search(r"(\.tau/manifests/manifest-\d{14}\.md)", text)
    if rel_match:
        return rel_match.group(1)

    # Fallback: any path ending with manifest-*.md (exclude /manifests/ prefix matches)
    fallback = re.search(r"(/[a-z][^\s]*manifest-[a-zA-Z0-9-]+\.md)", text)
    if fallback:
        return fallback.group(1)

    return None


def _validate_manifest(path: str) -> tuple[bool, str]:
    """Check manifest has required sections.

    Returns (is_valid, error_message).
    """
    manifest_path = Path(path)
    if not manifest_path.exists():
        return False, f"Manifest not found: {path}"

    fm = read_manifest_frontmatter(manifest_path)
    if fm is None:
        return False, f"Cannot read manifest: {path}"

    required_keys = {"id", "title", "goal", "status"}
    missing = required_keys - set(fm.keys())
    if missing:
        return False, f"Manifest missing frontmatter keys: {', '.join(sorted(missing))}"

    # Check required sections
    try:
        content = manifest_path.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"Cannot read manifest: {e}"

    required_sections = {"## Goal", "## Success Criteria", "## Subtasks"}
    content_upper = content.upper()
    missing_sections = []
    for section in required_sections:
        if section.upper() not in content_upper:
            missing_sections.append(section)

    if missing_sections:
        return False, f"Manifest missing sections: {', '.join(missing_sections)}"

    return True, ""


def _read_manifest_status(path: str) -> str | None:
    """Extract status from manifest frontmatter."""
    fm = read_manifest_frontmatter(Path(path))
    if fm is None:
        return None
    return fm.get("status")


def _find_executing_manifest(goal: str) -> str | None:
    """Find one executing manifest matching the goal.

    Searches .tau/manifests/ for manifests with status 'executing'
    whose goal contains the provided goal string (case-insensitive).
    """
    entries = load_manifests()
    goal_lower = goal.lower()
    for entry in entries:
        if entry.status != "executing":
            continue
        manifest_goal = entry.goal.lower()
        if goal_lower in manifest_goal or manifest_goal in goal_lower:
            return str(entry.path)
    return None


# ── Executor ──────────────────────────────────────────────────────

def _run_executor(
    agent: "TauErgon",
    manifest_path: str,
    ctx_path: str,
    max_depth: int,
    retry_budget: int,
) -> str:
    """Run the executor loop with tool restrictions.

    Returns a summary string with manifest path and status.
    """
    from agent_tool_filter import ToolFilter

    original_filter = agent.tool_filter
    agent.tool_filter = ToolFilter(
        allowlist=_ALLOWED_ORCHESTRATE_TOOLS,
        denied_message=(
            "Tool '{tool_name}' is not permitted in orchestrate executor mode. "
            "You are an executor — delegate work via fork/subagent, manage "
            "manifests, and read/analyze. Do not do work yourself. "
            "Available tools: {available_tools}."
        ),
    )

    try:
        agent.force_end_turn = None

        prompt = EXECUTOR_INSTRUCTIONS.format(
            manifest_path=manifest_path,
            ctx_path=ctx_path,
            max_depth=max_depth,
            retry_budget=retry_budget,
        )

        result = agent.invoke_with_tools(prompt)

        # Verify loop: continue if result is None (interrupted)
        # and manifest is not yet complete/failed.
        max_iterations = 20
        iteration = 0
        while result is None and iteration < max_iterations:
            iteration += 1
            status = _read_manifest_status(manifest_path)
            if status in ("complete", "failed"):
                break
            result = agent.invoke_with_tools(
                f"Continue executing manifest: {manifest_path}\n\n"
                f"Current status: {status or 'unknown'}\n\n"
                f"{EXECUTOR_INSTRUCTIONS.format(
                    manifest_path=manifest_path,
                    ctx_path=ctx_path,
                    max_depth=max_depth,
                    retry_budget=retry_budget,
                )}"
            )

        final_status = _read_manifest_status(manifest_path)
        return (
            f"Orchestrate executor completed.\n"
            f"Manifest: {manifest_path}\n"
            f"Status: {final_status or 'unknown'}\n"
            f"Iterations: {iteration}"
        )
    finally:
        agent.force_end_turn = None
        agent.tool_filter = original_filter


# ── Run ───────────────────────────────────────────────────────────

def run(
    goal: str,
    title: str = "",
    max_depth: int = 3,
    retry_budget: int = 2,
    resume: str = "",
    _ctx: ToolContext | None = None,
) -> str:
    """Run the orchestrate tool.

    1. Handle resume mode (skip fork phase)
    2. Check for auto-resume (one executing manifest matching goal)
    3. Fork phase: spawn fork with FORK_INSTRUCTIONS to prepare
    4. Extract manifest path from fork result
    5. Validate manifest
    6. Create .ctx file if missing
    7. Run executor via _run_executor()
    """
    agent = _ctx.agent if _ctx else None
    tool_call_id = _ctx.tool_call_id if _ctx else None

    # ── Handle resume mode ──────────────────────────────────────
    if resume:
        manifest_path = resume
        is_valid, err = _validate_manifest(manifest_path)
        if not is_valid:
            return f"Resume failed: {err}"

        ctx_path = str(Path(manifest_path).with_suffix(".ctx"))
        if agent is None:
            return "ERROR: orchestrate executor requires an agent (agent is None)"

        return _run_executor(agent, manifest_path, ctx_path, max_depth, retry_budget)

    # ── Auto-resume: find one executing manifest matching goal ──
    auto_resume = _find_executing_manifest(goal)
    if auto_resume:
        manifest_path = auto_resume
        ctx_path = str(Path(manifest_path).with_suffix(".ctx"))
        if agent is None:
            return "ERROR: orchestrate executor requires an agent (agent is None)"

        return (
            f"Auto-resuming manifest: {manifest_path}\n\n"
            f"{_run_executor(agent, manifest_path, ctx_path, max_depth, retry_budget)}"
        )

    # ── Fork phase ──────────────────────────────────────────────
    if agent is None:
        return "ERROR: orchestrate prepare requires an agent (agent is None)"

    from agent_subagent import NESTING_DEPTH_THRESHOLD

    if agent.nesting_count >= NESTING_DEPTH_THRESHOLD:
        return (
            f"ERROR: Maximum nesting depth ({NESTING_DEPTH_THRESHOLD}) exceeded. "
            f"Cannot spawn fork at depth {agent.nesting_count}."
        )

    # Spawn fork to prepare manifest + context
    fork_task = (
        f"Investigate and prepare a manifest for this goal:\n"
        f"\n"
        f"  Goal: {goal}\n"
        f"  Title: {title or goal}\n"
        f"  Max depth: {max_depth}\n"
        f"  Retry budget: {retry_budget}\n"
        f"\n"
        f"{FORK_INSTRUCTIONS}"
    )

    from agent_subagent import invoke_fork_sync

    fork_result = invoke_fork_sync(
        prompt=fork_task,
        parent_context=agent.context,
        parent_agent=agent,
        nesting_stack=agent.nesting_stack,
        nesting_type="F",
        tool_call_id=tool_call_id,
        tool_filter=None,  # Children always get unrestricted tool access.
    )

    # ── Extract manifest path ───────────────────────────────────
    manifest_path = _extract_manifest_path(fork_result)
    if manifest_path is None:
        return (
            "Fork completed but no manifest path found in output.\n"
            f"Fork output:\n{fork_result[:500]}"
        )

    # ── Validate manifest ───────────────────────────────────────
    is_valid, err = _validate_manifest(manifest_path)
    if not is_valid:
        return f"Manifest validation failed: {err}"

    # ── Ensure .ctx file exists ─────────────────────────────────
    ctx_path = str(Path(manifest_path).with_suffix(".ctx"))
    ctx_file = Path(ctx_path)
    if not ctx_file.exists():
        # Create a basic context file from fork output
        ctx_content = (
            "# Context for orchestrate\n"
            f"\n"
            f"## Goal\n"
            f"{goal}\n"
            f"\n"
            f"## Investigation Summary\n"
            f"{fork_result[:2000]}\n"
        )
        ctx_file.write_text(ctx_content, encoding="utf-8")

    # ── Executor phase ──────────────────────────────────────────
    return _run_executor(agent, manifest_path, ctx_path, max_depth, retry_budget)
