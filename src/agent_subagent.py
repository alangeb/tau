"""Subagent and Fork Spawning Module for TauErgon.

Delegation patterns:
- **Subagent**: Isolated agent with fresh context (blank slate).
- **Fork**: Agent inheriting parent's full conversation history.

Both create in-process TauErgon instances sharing parent config, tools, and skills.

Nesting restrictions prevent unbounded recursion:
  Level 0-1: Full capabilities.  Level 2+: No further subagents/forks.
"""

from __future__ import annotations

import copy
import logging
import os
import shutil
import tempfile
import time
from collections import deque
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from agent_config import Config
from agent_context import TauContext

if TYPE_CHECKING:
    from agent_core import TauErgon
    from agent_tool_filter import ToolFilter

logger = logging.getLogger(__name__)

__all__ = [
    "NESTING_DEPTH_THRESHOLD",
    "invoke_subagent_sync",
    "invoke_fork_sync",
]

# Default nesting depth threshold (exported for backward compatibility).
NESTING_DEPTH_THRESHOLD = 2

# Fork budget: maximum forks per session to prevent delegate loops
FORK_BUDGET = 20
FORK_BUDGET_WINDOW = 3600  # 1 hour window


# ── Fork isolation helpers ─────────────────────────────────────────────────


def _create_fork_isolation() -> tuple[str, Path]:
    """Return (fork_id, temp_dir) for resource isolation."""
    fork_id = str(uuid.uuid4())[:8]
    temp_dir = Path(tempfile.mkdtemp(prefix=f"tau-fork-{os.getpid()}-{fork_id}-"))
    return fork_id, temp_dir


def _cleanup_fork_isolation(temp_dir: Path) -> None:
    """Remove fork's isolated temp directory (best-effort)."""
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
    except OSError:
        pass


# ── Subagent creation ────────────────────────────────────────────────────


def _create_subagent(
    parent_agent: TauErgon,
    config: Config | None,
    tool_filter: ToolFilter | None,
) -> TauErgon:
    """Create a new TauErgon inheriting configuration from parent."""
    from agent_core import TauErgon

    return TauErgon(
        config=config if config is not None else getattr(parent_agent, "config", None),
        llm_group_name=parent_agent.current_group_name,
        max_context_tokens=parent_agent.max_context_tokens,
        tool_filter=tool_filter,
    )


# ── Nesting restriction text ─────────────────────────────────────────────


def _nesting_restriction_text(nesting_count: int) -> str:
    """Restriction text appended to system prompts near nesting limit."""
    return (
        f"[[You are already a subagent/fork running at nesting level "
        f"{nesting_count}: You MUST NOT use the fork tool, "
        f"You MUST NOT use the subagent tool, "
        f"You MUST NOT do further forks/subagents]]"
    )


def _nesting_restriction_suffix(nesting_count: int) -> str:
    """Restriction suffix appended to fork context near nesting limit."""
    return (
        f"\n\n[[You are running at nesting level {nesting_count}: "
        f"You MUST NOT use the fork tool, You MUST NOT use the subagent tool, "
        f"You MUST NOT do further forks/subagents]]"
    )


# ── Public API ───────────────────────────────────────────────────────────


def invoke_subagent_sync(
    prompt: str,
    system_prompt: str,
    parent_agent: TauErgon,
    nesting_count: int = 0,
    nesting_stack: str = "",
    tool_filter: ToolFilter | None = None,
    config: Config | None = None,
    nesting_threshold: int = 2,
) -> str:
    """Spawn an isolated subagent with a fresh context (no parent history).

    The subagent inherits tools and skills but starts with a blank conversation.
    Nesting restrictions are applied when depth exceeds the threshold.
    """
    subagent = _create_subagent(parent_agent, config, tool_filter)
    subagent.nesting_stack = nesting_stack + "S"
    subagent.original_task = prompt

    if nesting_count >= nesting_threshold - 1:
        system_prompt += _nesting_restriction_text(nesting_count)

    subagent.context = TauContext(
        [{"role": "system", "content": system_prompt}],
        nesting_stack=nesting_stack + "S"
    )

    # Track subagent lifecycle in audit log.
    parent_agent._session.audit_writer.subagent_start(prompt)
    start_time = time.monotonic()
    try:
        result = subagent.invoke_with_tools(prompt)
        # If the subagent was interrupted or exited (run_loop returned None),
        # surface the last substantive response instead of None, which the
        # tool executor would stringify to "None".
        if result is None:
            if subagent.last_substantive_response:
                result = (
                    "[Subagent interrupted — received exit/interrupt signal while working. "
                    f"Last substantive response was: {subagent.last_substantive_response}]"
                )
            else:
                result = (
                    "[Subagent interrupted — received exit/interrupt signal before any "
                    "substantive response was produced.]"
                )
        return result
    except Exception as e:
        error_msg = f"[Subagent crash: {type(e).__name__}: {e}]"
        logger.error("Subagent crashed: %s", error_msg, exc_info=True)
        return error_msg
    finally:
        duration_s = time.monotonic() - start_time
        parent_agent._session.audit_writer.subagent_end(duration_s)


def invoke_fork_sync(
    prompt: str,
    parent_context: TauContext,
    parent_agent: TauErgon,
    nesting_stack: str = "",
    nesting_type: str = "F",
    tool_call_id: str | None = None,
    tool_filter: ToolFilter | None = None,
    config: Config | None = None,
    nesting_threshold: int = 2,
) -> str:
    """Spawn a fork inheriting a deep copy of the parent context.

    The fork receives the full parent conversation history. Pending tool calls
    are marked PENDING; the fork's own call is marked FORK as responder.
    Nesting restrictions are applied when depth exceeds the threshold.

    Delegate loop protection: if the same task is forked repeatedly,
    a soft reject is issued on the first duplicate (with explanation),
    but the second duplicate is allowed to prevent blocking legitimate retries.

    Args:
        prompt: Task description for the fork.
        parent_context: Parent's TauContext (deep-copied for fork).
        parent_agent: Parent TauErgon instance.
        nesting_stack: Parent's nesting stack string (e.g., "SF" = subagent→fork).
        nesting_type: Single char appended to stack (F=fork, T=think, H=heartbeat, K=skill).
        tool_call_id: Optional tool call ID to mark as FORK responder.
        tool_filter: Optional tool filter for the fork.
        config: Optional config (inherits from parent if None).
        nesting_threshold: Depth at which nesting restrictions apply.
    """
    # ── Delegate loop detection (soft reject) ──
    tracker = getattr(parent_agent, "_fork_loop_tracker", None)
    if tracker is None:
        tracker = {
            "tasks": deque(maxlen=200),  # Bounded to prevent memory leak
            "warned": set(),
            "timestamps": deque(maxlen=FORK_BUDGET + 10),  # Bounded to prevent memory leak
        }
        parent_agent._fork_loop_tracker = tracker

    # ── Fork budget check ──
    now = time.monotonic()
    tracker["timestamps"] = deque(
        (t for t in tracker["timestamps"] if now - t < FORK_BUDGET_WINDOW),
        maxlen=FORK_BUDGET + 10,
    )
    if len(tracker["timestamps"]) >= FORK_BUDGET:
        logger.warning(
            "Fork budget exhausted: %d forks in last %d seconds. "
            "Blocking further forks to prevent delegate loops.",
            FORK_BUDGET, FORK_BUDGET_WINDOW,
        )
        return (
            f"⚠️  Fork budget exhausted ({FORK_BUDGET} forks in last {FORK_BUDGET_WINDOW}s).\n"
            f"\nFurther forks have been BLOCKED to prevent delegate loops.\n\n"
            f"Summarize your findings and return to the parent. "
            f"Do NOT fork again until the budget resets.\n"
        )
    tracker["timestamps"].append(now)

    normalized = prompt.strip().lower()[:200]  # Normalize for comparison
    # Prune tasks by the same time window so duplicate detection only
    # considers recent forks (prevents unbounded growth + stale counts).
    tracker["tasks"] = deque(
        ((t, n) for (t, n) in tracker["tasks"] if now - t < FORK_BUDGET_WINDOW),
        maxlen=200,
    )
    task_count = sum(1 for (t, n) in tracker["tasks"] if n == normalized)

    # Periodically clean up warned set to prevent unbounded growth
    if len(tracker["warned"]) > 100:
        tracker["warned"] = set()

    tracker["tasks"].append((now, normalized))

    if task_count >= 1 and normalized not in tracker["warned"]:
        # First duplicate — soft reject with explanation
        tracker["warned"].add(normalized)
        logger.warning(
            "Delegate loop detected: task forked %d times. "
            "This fork is allowed, but repeated identical forks suggest "
            "the parent should summarize results and terminate instead. "
            "On the NEXT duplicate, the fork will be blocked.",
            task_count + 1,
        )
    elif task_count >= 2:
        # Second+ duplicate — allow but log
        logger.warning(
            "Repeated fork #%d of same task. Consider terminating "
            "the delegation loop and summarizing results.",
            task_count + 1,
        )

    fork_id = ""
    temp_dir: Path | None = None
    try:
        fork_id, temp_dir = _create_fork_isolation()

        # Pass parent audit file path and nesting level to fork for unified audit logging.
        # Fork reads these via os.getenv() during AuditWriter lazy init.
        # We set them briefly and clean up in finally to limit subprocess inheritance window.
        parent_audit_file = str(parent_agent._session.audit_file)
        try:
            os.environ["TAU_PARENT_AUDIT_FILE"] = parent_audit_file
            os.environ["TAU_FORK_NESTING"] = nesting_stack + nesting_type

            fork = _create_subagent(parent_agent, config, tool_filter)
        finally:
            # Unset env vars immediately after subagent creation.
            # The AgentSessionManager has already read them during __init__.
            # This prevents subprocesses spawned by the fork (e.g., bash tool)
            # from inheriting these internal vars.
            # Uses finally to ensure cleanup even if _create_subagent() raises.
            os.environ.pop("TAU_PARENT_AUDIT_FILE", None)
            os.environ.pop("TAU_FORK_NESTING", None)
        fork.nesting_stack = nesting_stack + nesting_type
        fork.original_task = prompt

        fork.context = TauContext(
            copy.deepcopy(parent_context.to_list()),
            nesting_stack=nesting_stack + nesting_type
        )

        nesting_suffix = ""
        if fork.nesting_count >= nesting_threshold - 1:
            nesting_suffix = _nesting_restriction_suffix(fork.nesting_count)

        # Only pass fork_tool_call_id if it exists in the parent's pending tool calls.
        # The fork context is a deep copy of parent messages — if the tool_call_id
        # is not in the parent's pending calls, it won't be found in the fork's context,
        # triggering a spurious "no pending calls to mark" validation warning.
        effective_tool_call_id = None
        if tool_call_id is not None:
            parent_pending = parent_context.get_pending_tool_ids()
            if tool_call_id in parent_pending:
                effective_tool_call_id = tool_call_id
            else:
                logger.debug(
                    "fork_tool_call_id '%s' not in parent pending calls %s — "
                    "passing None to avoid spurious warning",
                    tool_call_id, sorted(parent_pending),
                )

        fork.context.prepare_fork_context(
            task=(
                "You successfully forked! You are the fork now. "
                "Work exactly on this TASK (do not work on other things - they will be taken care of), "
                "then end your turn with a plain text response. "
                "TASK: {prompt}"
            ),
            fork_tool_call_id=effective_tool_call_id,
            nesting_suffix=nesting_suffix,
        )

        # Track fork lifecycle in audit log.
        parent_agent._session.audit_writer.fork_start(prompt)
        start_time = time.monotonic()
        try:
            result = fork.invoke_with_tools(f"{prompt}")
            # If the fork was interrupted or exited (run_loop returned None),
            # surface the last substantive response instead of None, which the
            # tool executor would stringify to "None".
            if result is None:
                if fork.last_substantive_response:
                    result = (
                        "[Fork interrupted — received exit/interrupt signal while working. "
                        f"Last substantive response was: {fork.last_substantive_response}]"
                    )
                else:
                    result = (
                        "[Fork interrupted — received exit/interrupt signal before any "
                        "substantive response was produced.]"
                    )
        except Exception as e:
            error_msg = f"[Fork crash: {type(e).__name__}: {e}]"
            logger.error("Fork crashed: %s", error_msg, exc_info=True)
            return error_msg
        duration_s = time.monotonic() - start_time
        parent_agent._session.audit_writer.fork_end(duration_s)

        parent_context.clear_fork_metadata()

        return result
    finally:
        if temp_dir is not None:
            _cleanup_fork_isolation(temp_dir)
        # Clean up audit env vars so they don't leak to subsequent operations.
        os.environ.pop("TAU_PARENT_AUDIT_FILE", None)
        os.environ.pop("TAU_FORK_NESTING", None)
