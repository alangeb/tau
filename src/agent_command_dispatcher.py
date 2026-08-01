"""Context management and restart logic for TauErgon.

Encapsulates context operations and restart logic that were previously
part of the TauErgon class. This module provides focused classes for
managing context lifecycle and agent restart.

Key Components
- ContextManager: Manages context loading, saving, and restoration
- RestartManager: Handles agent restart with preserved state
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from agent_console import (
    context_list_display,
    context_preview_display,
    context_restored,
    context_restore_failure,
    echo,
    no_context_file_found,
    print_agent_exit_summary,
    restart_fallback_failure,
    restart_failure,
    restart_flow,
    undo_message,
    warning,
)
from agent_input import (
    get_context_file_by_parent_ppid,
    list_context_files,
    preview_context,
)
from agent_context_utils import get_all_context_files as _get_all_context_files
from agent_project import (
    find_project_root,
    get_all_entries,
    get_entry_info,
    get_loadable_contexts,
)
from agent_session import LOG_DIR, SESSION_PREFIX

if TYPE_CHECKING:
    from agent_core import TauErgon


class ContextManager:
    """Manage context operations: loading, saving, undo, and restoration.

    Handles context file operations, plan/audit file copying, and
    context restoration from previous sessions.
    """

    def __init__(self, agent: TauErgon) -> None:
        """Initialize context manager with reference to the TauErgon instance.

        Args:
            agent: The TauErgon instance this manager belongs to.
        """
        self._agent = agent

    def clear(self) -> str:
        """Clear all messages except the system prompt and reset token counters.

        Returns:
            str: Confirmation message "Context cleared."
        """
        self._agent.context.clear()
        self._agent._session.clear_tokens()
        return "Context cleared."

    def undo(self) -> None:
        """Undo the last conversation turn.

        Removes messages from the last user message onward, effectively
        reverting the last turn. This allows correcting mistakes or trying
        a different approach.

        Displays the number of messages removed via the console.
        """
        old_len = len(self._agent.context)
        self._agent.context.undo()
        undo_message(old_len - len(self._agent.context))

    def load_context_by_id(self, idx: int) -> dict | None:
        """Load a context file by its ID from the context list.

        Retrieves a context file entry from the list of available contexts
        using a 1-based index.

        Args:
            idx: 1-based index of the context to load.

        Returns:
            dict | None: The context dictionary containing 'name' and 'file' keys
                if the ID is valid, otherwise None.

        Displays:
            - Error message if ID is out of range
        """
        contexts = list_context_files()
        if not contexts or idx < 1 or idx > len(contexts):
            echo(f"ID {idx} out of range (1-{len(contexts)})")
            return None
        return contexts[idx - 1]

    def copy_plan_file(self, old_context_file: Path) -> None:
        """Copy the old session's .plan file to the new session's plan path.

        Called after /continue loads a context from a previous session so that
        plan entries survive session restoration.
        """
        old_plan = old_context_file.with_suffix(".plan")
        if not old_plan.exists():
            return

        if not SESSION_PREFIX:
            return

        new_plan = LOG_DIR / f"{SESSION_PREFIX}.plan"
        if old_plan != new_plan:
            try:
                shutil.copy2(old_plan, new_plan)
            except OSError as e:
                warning(f"Failed to copy plan file {old_plan} -> {new_plan}: {e}")

    def copy_audit_file(self, old_context_file: Path) -> None:
        """Copy the old session's .audit file into the current session's audit file.

        Called after /continue loads a context from a previous session so that
        /audit shows the full history (old + new session records).

        Appends old audit content to the current audit file so the audit writer
        can continue writing to the same file without losing history.
        """
        old_audit = old_context_file.with_suffix(".audit")
        if not old_audit.exists():
            return

        new_audit = self._agent._session.audit_file
        if old_audit != new_audit:
            try:
                with open(old_audit, "r", encoding="utf-8") as src:
                    content = src.read()
                with open(new_audit, "a", encoding="utf-8") as dst:
                    dst.write(content)
            except OSError as e:
                warning(f"Failed to copy audit file {old_audit} -> {new_audit}: {e}")

    def handle_continue(self, args: str) -> None:
        """Handle the /continue command to load previous contexts.

        Supports multiple subcommands for loading and previewing saved contexts:
        - No arguments: Load the latest context from the same terminal session
        - "list": List saved contexts (default 25, or specify count)
        - "<n>": Load context by ID
        - "preview <n>": Preview the last 3 messages of context by ID
        - "project": Load most recent project context (.tau/contexts)
        - "project <n>": Load project context by index (0=most recent)
        - "project list": List project context chain

        Args:
            args: Command arguments. Examples:
                - "" (empty) - Load latest context
                - "list" - List contexts
                - "list 50" - List last 50 contexts
                - "5" - Load context #5
                - "preview 5" - Preview context #5
                - "project" - Load most recent project context
                - "project 0" - Same as above
                - "project -1" - Second most recent
                - "project list" - List project chain

        Displays:
            - Context restoration success/failure messages
            - List of contexts for "list" subcommand
            - Preview of context for "preview" subcommand
            - Usage help for invalid arguments
        """
        if not args:
            self._handle_continue_default()
            return

        parts = args.split(maxsplit=1)
        sub_cmd = parts[0].lower()

        if sub_cmd == "rebuild":
            self._handle_continue_rebuild()
        elif sub_cmd == "list":
            self._handle_continue_list(parts[1] if len(parts) > 1 else "")
        elif sub_cmd == "preview":
            self._handle_continue_preview(parts[1] if len(parts) > 1 else "")
        elif sub_cmd == "project":
            self._handle_continue_project(parts[1] if len(parts) > 1 else "")
        else:
            self._handle_continue_load_by_id(args)

    def _handle_continue_default(self) -> None:
        """Load the latest context from the same terminal session."""
        target_ctx = get_context_file_by_parent_ppid()
        # Skip current session's own context file — look for the previous one
        if target_ctx and target_ctx == self._agent._session.context_file:
            target_ctx = self._get_previous_context_file()
        if target_ctx:
            self._agent._session.context_file = target_ctx
            if self._agent.context.load_from_file(self._agent._session.context_file):
                self.copy_plan_file(target_ctx)
                self.copy_audit_file(target_ctx)
                context_restored(len(self._agent.context), target_ctx)
            else:
                context_restore_failure(target_ctx)
        else:
            no_context_file_found()

    def _handle_continue_rebuild(self) -> None:
        """Rebuild session registry from LOG_DIR and report results."""
        try:
            from agent_session_registry import get_registry, REGISTRY_FILE
        except ImportError:
            echo("[continue] Session registry module not available.")
            return

        echo("[continue] Rebuilding session registry...")
        registry = get_registry()

        # Invalidate cache to force reload, then rebuild
        registry._invalidate()
        found = registry.rebuild()

        total = len(registry.list_sessions())
        active = len(registry.list_sessions(status="active"))
        archived = len(registry.list_sessions(status="archived"))

        echo(f"[continue] Found {found} new session(s) in LOG_DIR")
        echo(f"[continue] Total sessions: {total} (active: {active}, archived: {archived})")
        echo(f"[continue] Registry: {REGISTRY_FILE}")

    def _get_previous_context_file(self) -> Path | None:
        """Get the previous context file (skip current session's own file).

        Uses the session registry if available, falling back to scanning
        LOG_DIR directly.
        """
        ppid = os.getppid()
        ctx_pattern = re.compile(rf"^{ppid}_\d+_\d+\.context$")
        current = self._agent._session.context_file

        # Try registry first
        try:
            from agent_session_registry import get_registry
            ctx_files = get_registry().get_context_files(include_archived=True)
        except Exception:
            ctx_files = []

        # Filter by parent PID, excluding current session
        matching = [
            f for f in ctx_files
            if ctx_pattern.match(f.name) and f != current
        ]
        if matching:
            return max(matching, key=lambda f: f.stat().st_mtime)

        # Fallback: all context files except current
        all_ctx = _get_all_context_files()
        others = [f for f in all_ctx if f != current]
        return others[0] if others else None

    def _handle_continue_list(self, n_str: str) -> None:
        """List saved contexts.

        Args:
            n_str: Optional count argument. Defaults to 25 if empty or invalid.
        """
        n = int(n_str) if n_str.strip().isdigit() and int(n_str) > 0 else 25
        if n_str.strip() and not n_str.strip().isdigit():
            echo("Usage: /continue list [<n>]")
            return
        context_list_display(list_context_files(limit=n))

    def _handle_continue_preview(self, idx_str: str) -> None:
        """Preview the last 3 messages of a context by ID.

        Args:
            idx_str: The context ID to preview.
        """
        if not idx_str.strip():
            echo("Usage: /continue preview <n>")
            return
        try:
            idx = int(idx_str.strip())
        except ValueError:
            echo(f"Invalid ID: {idx_str.strip()}")
            return
        ctx = self.load_context_by_id(idx)
        if ctx is None:
            return
        context_preview_display(ctx["name"], preview_context(ctx["file"]))

    def _handle_continue_load_by_id(self, args: str) -> None:
        """Load a context by numeric ID.

        Args:
            args: The numeric ID string.
        """
        try:
            idx = int(args.strip())
        except ValueError:
            echo(
                f"Unknown /continue argument: {args}\n"
                f"Usage: /continue | /continue list [<n>] | /continue <n> | /continue preview <n>"
            )
            return
        ctx = self.load_context_by_id(idx)
        if ctx is None:
            return
        self._agent._session.context_file = ctx["file"]
        if self._agent.context.load_from_file(self._agent._session.context_file):
            self.copy_plan_file(self._agent._session.context_file)
            self.copy_audit_file(self._agent._session.context_file)
            context_restored(len(self._agent.context), self._agent._session.context_file)
        else:
            context_restore_failure(self._agent._session.context_file)

    def _handle_continue_project(self, args: str) -> None:
        """Handle ``/continue project`` to load from the project context chain.

        Usage:
            /continue project           Load most recent project context
            /continue project 0         Same as above (0 = most recent)
            /continue project -1        Second most recent
            /continue project -2        Third most recent
            /continue project list      Show the full chain

        Indexing: 0 = most recent, abs(N) = offset from end.
        The current session's context file is skipped to avoid re-loading
        the in-progress session.
        """
        project_dir = find_project_root()
        if project_dir is None:
            echo("No project found. Run `tau --init-project` to initialize a project.")
            return

        current_ctx = self._agent._session.context_file
        # Filter out the current session's context file and empty/malformed files
        loadable = [p for p in get_loadable_contexts(project_dir) if p != current_ctx]

        if not args:
            if not loadable:
                if get_all_entries(project_dir):
                    echo("All project contexts are the current session or empty. No previous contexts to load.")
                else:
                    echo("No contexts saved in this project yet.")
            else:
                idx = len(loadable) - 1
                self._load_project_context(loadable[idx])
            return

        parts = args.split(maxsplit=1)
        sub_cmd = parts[0].lower()

        if sub_cmd == "list":
            entries = get_entry_info(project_dir)
            if not entries:
                echo("No contexts saved in this project.")
                return
            context_list_display(entries)
            return

        try:
            n = int(sub_cmd)
        except ValueError:
            echo(
                f"Unknown /continue project argument: {args}\n"
                "Usage: /continue project | /continue project <N> | /continue project list"
            )
            return

        offset = abs(n)
        idx = len(loadable) - 1 - offset
        if idx < 0:
            echo(
                f"Context at index {n} not found or stale "
                f"(project has {len(get_all_entries(project_dir))} entries, "
                f"{len(loadable)} loadable)."
            )
            return
        self._load_project_context(loadable[idx])

    def _load_project_context(self, ctx_path: Path) -> None:
        """Load a project context file, copying plan and audit files."""
        self._agent._session.context_file = ctx_path
        if self._agent.context.load_from_file(self._agent._session.context_file):
            self.copy_plan_file(self._agent._session.context_file)
            self.copy_audit_file(self._agent._session.context_file)
            context_restored(len(self._agent.context), self._agent._session.context_file)
        else:
            context_restore_failure(self._agent._session.context_file)


class RestartManager:
    """Handle agent restart with preserved state.

    Manages the restart process: filtering CLI args, saving context,
    clearing bytecode cache, and exec'ing the agent process.
    """

    def __init__(self, agent: TauErgon) -> None:
        """Initialize restart manager with reference to the TauErgon instance.

        Args:
            agent: The TauErgon instance to restart.
        """
        self._agent = agent

    def handle_restart(self, restart_args: str) -> None:
        """Restart the agent with the same configuration.

        Restarts the agent process while preserving the current context and
        configuration. Filters out irrelevant flags and ensures the -c flag
        is set to continue from the saved context.

        Args:
            restart_args: Additional arguments to pass to the restarted agent.

        Displays:
            - Restart command being executed
            - Error messages if restart fails

        Actions:
            - Saves current context to file
            - Clears bytecode cache
            - Attempts execvp for clean restart
            - Falls back to subprocess.Popen if execvp fails
        """
        self._agent._session.clear_tokens()  # Clear stale cache stats from previous session

        filtered_args = self._filter_cli_args()

        if not any(arg in ("-c", "--continue") for arg in filtered_args):
            filtered_args.append("-c")

        cmd = [sys.executable, sys.argv[0]] + filtered_args
        if restart_args:
            cmd.extend(restart_args.split())

        restart_flow(" ".join(cmd))
        print_agent_exit_summary(self._agent)
        self._agent.context.close_turn("[Restart]")
        self._agent.context.save_to_file(self._agent._session.context_file, force=True)

        # Clear bytecode cache
        for cache_dir in ("tools/__pycache__", "__pycache__"):
            path = Path(__file__).parent / cache_dir
            if path.exists():
                shutil.rmtree(path)

        try:
            os.execvp(cmd[0], cmd)
        except OSError as e:
            restart_failure(str(e))
            try:
                subprocess.Popen(cmd)
            except OSError as e2:
                restart_fallback_failure(str(e2))
        sys.exit(0)

    def _filter_cli_args(self) -> list[str]:
        """Filter CLI arguments for restart.

        Removes flags that are irrelevant to the restarted agent (--pid, --card,
        --timeout, --list, etc.) while preserving all other arguments.

        Returns:
            list[str]: Filtered argument list.
        """
        skip_flags = {
            "--pid",
            "--card",
            "--timeout",
            "--list",
            "--list-all",
            "--listjson",
            "--listjson-all",
            "--query",
            "--init-project",
        }

        filtered_args: list[str] = []
        i = 0
        while i < len(sys.argv[1:]):
            arg = sys.argv[i + 1]  # +1 because sys.argv[0] is script name
            if arg in skip_flags:
                i += 2
                continue
            if not arg.startswith("-"):
                i += 1
                continue
            filtered_args.append(arg)
            if (
                "=" not in arg
                and i + 2 < len(sys.argv)
                and not sys.argv[i + 2].startswith("-")
            ):
                filtered_args.append(sys.argv[i + 2])
                i += 2
            else:
                i += 1

        return filtered_args