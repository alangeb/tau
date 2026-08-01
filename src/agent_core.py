"""TauErgon Core Module

Core functionality for TauErgon system: tool calling, context management, hierarchical agent orchestration.

Key Components
- TauErgon: Main agent class, orchestrates agent lifecycle
- ToolFilter: Filters tools via allowlist/blocklist
- invoke_with_tools(): Entry point for user interactions
- invoke_with_tools_loop(): Core tool calling loop
- run(): Starts agent

Architecture
Message-driven:
1. User Input: Messages appended via invoke_with_tools(), validated for OpenAI compliance
2. LLM Interaction: invoke_with_tools_loop() manages request/response cycle, tool calling, retry logic
3. Tool Execution: execute_tool_batch() parses tool calls, appends results to context
4. Context Management: TauContext maintains history, auto-compresses near token limits
5. Hierarchical Delegation: Subagents (isolated), Fork (inherits parent), Delegate mode (orchestrator)
6. Safety: Loop detection, end-of-turn validation, interrupt/exit flags

Entry Points
- invoke_with_tools(user_input): Send message, execute tools, return response
- invoke_with_tools_loop(): Core loop (context must end with user message)
- run(inputs, interactive): Start agent with input handling

Commands
Slash commands (/help, /exit, /subagent) dispatched via _handle_command(). Custom commands loadable from commands/ directory.

Tools
Registered in TOOLS registry, filtered via ToolFilter. execute_tool_batch() handles parallel execution with error handling.

Thread Safety
System-wide flags (_interrupted, _exit_requested) for cooperative shutdown. Heartbeat runs in separate threads.

Example
    from agent_core import TauErgon
    from agent_audit_bridge import log_console_warning
from agent_config import Config
    config = Config.load()
    agent = TauErgon(config=config, agent_name="my-agent")
    response = agent.invoke_with_tools("What can you help me with?")
    print(response)

See Also
- agent_context: Context management
- agent_tool_executor: Tool execution
- agent_subagent: Subagent and fork invocation
- agent_commands: Command handling
"""

from __future__ import annotations

import os
import queue
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from agent_console import (
    assistant_message_display,
    exec_tool_fail,
    exec_usage,
    no_run_function_error,
    show_help,
    unknown_command_error,
    unknown_tool_error,
    warning,
)
from agent_command_dispatcher import ContextManager, RestartManager
from agent_command_handlers import CommandHandlersMixin
from agent_commands import CommandManager
from agent_config import Config
from agent_context import TauContext
from agent_init import resolve_agent_init
from agent_input import InputHandler
from agent_llm_client import SimpleOpenAIClient
from agent_loop import run_loop
from agent_models import AgentStatus, InputMessage
from agent_reflection import ReflectionScheduler
from agent_tool_filter import ToolFilter
from tools import ToolContext, TOOLS

if TYPE_CHECKING:
    from agent_audit_writer import AuditWriter


# ── Safe template substitution ─────────────────────────────────────────────

_SAFE_PLACEHOLDER_RE = re.compile(r'\{(\w+)\}')


def _safe_format_template(template: str, **kwargs: str) -> str:
    """Replace {placeholder} with values, leaving everything else untouched.

    Only replaces placeholders whose names are in *kwargs*.  Unknown
    placeholders are left as-is (no crash, no code execution).  Literal
    ``{{`` and ``}}`` are passed through unchanged because the regex
    only matches single-brace ``{word}`` patterns.

    This replaces the previous ``str.format()`` call which could execute
    arbitrary Python expressions (e.g. ``{__import__('os').system('cmd')}``).
    """
    values = {k: str(v) for k, v in kwargs.items()}

    def _replace(m: re.Match) -> str:
        name = m.group(1)
        return values.get(name, m.group(0))  # Leave unknown as-is

    return _SAFE_PLACEHOLDER_RE.sub(_replace, template)


__all__ = [
    "ToolFilter",
    "TauErgon",
]


class TauErgon(CommandHandlersMixin):
    MAX_OUTER_RECOVERY = 5  # Max recovery attempts before forced termination
    """Chat agent with tool calling, context management, loop detection, and subagent support.

    The TauErgon is the main orchestrator for AI agent interactions, providing:
    - Tool calling with OpenAI function-calling format
    - Context management with automatic compression
    - Loop detection to prevent infinite cycles
    - Subagent and fork support for hierarchical task delegation
    - Command handling for interactive control
    - Heartbeat mechanism for idle detection

    Attributes:
        config: Configuration object for the agent.
        agent_name: Name identifier for this agent instance.
        tool_filter: ToolFilter instance for filtering available tools.
        context: TauContext instance holding conversation history.
        client: SimpleOpenAIClient for LLM communication.
        loop_detector: LoopDetector for detecting conversation loops.
        available_tool_names: List of currently available tool names.
    """

    def __init__(
        self,
        config: Config | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_context_tokens: int | None = None,
        agent_name: str | None = None,
        tool_filter: "ToolFilter | None" = None,
        llm_group_name: str | None = None,
        heartbeat_seconds: int | None = None,
    ):
        """Initialize the TauErgon with configuration and resources.

        Sets up the agent with the provided configuration, initializing the LLM
        client, context, tool filtering, and various subsystems. Configuration
        priority: explicit argument > config object > defaults/errors.

        Args:
            config: Configuration object containing LLM settings, loop detection,
                heartbeat, and other agent parameters.
            base_url: Optional override for LLM API base URL.
            model: Optional override for LLM model name.
            max_context_tokens: Optional override for maximum context size.
            agent_name: Optional name identifier for this agent instance.
            tool_filter: Optional ToolFilter instance for filtering tools.
                Defaults to ToolFilter() if not provided.
            llm_group_name: Optional LLM group name to use. Defaults to the
                first available group or config.llm_group_name.
            heartbeat_seconds: Optional heartbeat interval in seconds. If set,
                enables heartbeat checking for idle detection.

        Raises:
            ValueError: If no LLM group is found in the configuration.
        """
        # Resolve all config + overrides into a single, fully-resolved config.
        init = resolve_agent_init(
            config=config,
            base_url=base_url,
            model=model,
            max_context_tokens=max_context_tokens,
            agent_name=agent_name,
            llm_group_name=llm_group_name,
            heartbeat_seconds=heartbeat_seconds,
        )

        self.config = config
        self.agent_name = init.agent_name
        self.tool_filter = tool_filter or ToolFilter()
        self.llm_groups = init.llm_groups

        self.current_group_name = init.current_group_name
        self._llm_model_override = init.model_override
        self._llm_base_url_override = init.base_url_override
        self._llm_context_override = init.max_context_tokens_override

        self.model_name = init.model_name
        self.base_url = init.base_url
        self._current_api_key = init.api_key
        self.max_context_tokens = init.max_context_tokens

        self.max_silent_retries = init.max_silent_retries
        self.max_enhanced_retries = init.max_enhanced_retries
        self.max_explicit_retries = init.max_explicit_retries

        from agent_llm_cache import PrefixCacheTracker

        self._cache_tracker = PrefixCacheTracker()
        self.client = SimpleOpenAIClient(
            base_url=self.base_url,
            api_key="",
            timeout=init.timeout,
            cache_tracker=self._cache_tracker,
        )
        self.context: TauContext = TauContext()
        self.context.set_metadata(
            pid=os.getpid(),
            working_dir=os.getcwd(),
            start_time=datetime.now().isoformat(),
            model=init.model_name,
            agent_name=init.agent_name,
        )

        self._sandbox_last_call: str | None = None  # sandbox double-call confirmation (see _run_sandbox_command)
        self.inference_params = init.inference_params

        self.max_tokens = init.max_tokens

        self._init_subsystems(init)

    # ── Subsystem initialization ──────────────────────────────────────────

    def _init_subsystems(self, init: "AgentInitConfig") -> None:
        """Initialize all agent subsystems.

        Delegates to agent_subsystems.init_subsystems() which creates and
        wires up: session manager, loop detector, reflection scheduler,
        loop escalation manager, EOT protection, and heartbeat manager.

        State variables and None placeholders are initialized directly
        as assignments after the bundle is returned.

        Called once from ``__init__`` after config resolution.
        """
        from agent_subsystems import init_subsystems, read_system_prompt

        # Load system prompt (needs session paths for template substitution)
        system_prompt = read_system_prompt()

        # Initialize all subsystems
        bundle = init_subsystems(self, init)

        # Assign subsystems to self
        self._session = bundle.session
        self.loop_detector = bundle.loop_detector
        self.reflection_scheduler = bundle.reflection_scheduler
        self._loop_escalation = bundle.loop_escalation
        self._eot_protection = bundle.eot_protection
        self._heartbeat = bundle.heartbeat

        # Assign tool names
        self.available_tool_names = bundle.available_tool_names

        # Initialize state variables directly (NOT in the bundle)
        self.nesting_stack: str = ""  # e.g. "SF" = fork in subagent
        self.original_cwd = Path.cwd()
        self._start_time = time.time()
        self.original_task: str | None = None
        self._cmd_dispatch_depth = 0
        self.force_end_turn: str | None = None
        self.last_substantive_response: str | None = None

        # Vision / image queue
        self._queued_images: list[tuple[str, str, str, str]] = []
        self._vision_supported: bool | None = None
        self._last_injected_tool_call_ids: list[str] = []

        # A2A state
        self._pending_a2a_responses: dict[str, dict] = {}
        self._pending_a2a_chunks: dict[str, list[dict]] = {}  # request_id -> list of chunk dicts
        self._current_a2a_request_id: str | None = None  # Set during A2A query processing

        # Turn active tracking (for status endpoint / tauweb running/idle detection)
        self._turn_active: bool = False

        # Control queue (inter-process supervision)
        self._control_queue: queue.Queue[str] = queue.Queue(maxsize=100)
        self._parent_pid: int | None = None

        # Commands
        self.available_commands: dict[str, Any] = {}
        self._commands_directory = None

        # Context and restart managers
        self._context_manager = ContextManager(self)
        self._restart_manager = RestartManager(self)

        # Input / threading state
        self.input_queue: queue.Queue = queue.Queue()
        self._a2a_listener_thread = None
        self._input_thread = None
        self._input_thread_stop = threading.Event()
        self._a2a_server = None
        self._keep_alive = False

        # Set system prompt in context
        self.context.set_system(system_prompt)

        # Log session start with full system prompt and tool schema
        self._session.audit_writer.session_start(
            model=self.model_name,
            tool_count=len(self.available_tool_names),
            cwd=os.getcwd(),
            system_prompt=self.context.get_system() or "",
            tool_schema=self.get_all_tools(),
        )

    # ── Vision / image queue management ──────────────────────────────────────

    def _inject_queued_images(self) -> None:
        """Inject all queued images as a single multimodal user message.

        Maintains clean OpenAI alternation:
          tool_results → synthetic_assistant → user(images)

        The synthetic assistant bridge is required because `append_user` after
        tool results triggers a validation warning. The bridge preserves the
        tool→assistant→user alternation pattern.
        """
        if not self._queued_images:
            return

        # Build multimodal content blocks: all images first, then combined text
        # Gemma 4 requires images BEFORE text; Qwen3.6 is flexible
        content_blocks: list[dict] = []
        descriptions: list[str] = []

        for data_uri, mime_type, description, _tool_call_id in self._queued_images:
            content_blocks.append({
                "type": "image_url",
                "image_url": {"url": data_uri},
            })
            if description:
                descriptions.append(description)

        # Add combined description text if any images had descriptions
        if descriptions:
            content_blocks.append({
                "type": "text",
                "text": "\n".join(descriptions),
            })

        # 1. Append synthetic assistant bridge (maintains alternation)
        self.context.append_assistant(
            "[Images loaded from see tool — continuing.]",
            synthetic=True,
        )

        # 2. Append user message with all images
        self.context.append_user(content_blocks, user_type="real")

        # 3. Track tool_call_ids for potential recovery, then clear queue
        self._last_injected_tool_call_ids = [
            entry[3] for entry in self._queued_images
        ]
        self._queued_images.clear()

    def _recover_from_vision_error(self) -> bool:
        """Recover from a vision-incompatible model error.

        Steps:
        1. Pop the user message containing images
        2. Pop the synthetic assistant bridge
        3. Mark see tool results as errors in-context
        4. Cache vision capability as False

        Returns True if recovery was performed, False if context didn't match
        expected pattern (recovery not possible).
        """
        msgs = self.context._messages
        if len(msgs) < 2:
            return False

        last = msgs[-1]
        second_last = msgs[-2]

        # Verify last message is a user message with image blocks
        if last.get("role") != "user":
            return False
        content = last.get("content", [])
        if not isinstance(content, list):
            return False
        has_images = any(b.get("type") == "image_url" for b in content)
        if not has_images:
            return False

        # Verify second-to-last is our synthetic assistant bridge
        if second_last.get("role") != "assistant":
            return False
        assistant_content = second_last.get("content", "")
        if "[Images loaded from see tool" not in str(assistant_content):
            return False

        # Collect tool_call_ids before popping (needed for marking errors)
        queued_ids = list(self._last_injected_tool_call_ids)

        # Pop both messages
        self.context._messages.pop()  # user (images)
        self.context._messages.pop()  # assistant (bridge)

        # Mark see tool results as errors in the context
        # Find tool results matching the queued tool_call_ids and modify in-place
        for msg in self.context._messages:
            if msg.get("role") == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                if tool_call_id in queued_ids:
                    msg["content"] = (
                        "Error: This model does not support vision. "
                        "Do not call see again."
                    )

        # Cache vision capability and clear tracking
        self._vision_supported = False
        self._last_injected_tool_call_ids.clear()
        return True

    # ── Control queue ────────────────────────────────────────────────────────

    def _process_control_queue(self) -> None:
        """Process pending control commands from parent supervisor.

        To be called at turn boundaries by supervisor integration (TASK_05b).
        Commands are consumed from the queue and applied to the agent's state.

        Command types:
        - inject: Append synthetic user message to context
        - terminate: Graceful (finish turn), forceful (exit immediately), or force_kill (SIGKILL)
        - redirect: Clear context and stale state, start new task
        - status: Log current status to audit
        """
        import json as _json

        processed = 0
        while not self._control_queue.empty():
            try:
                cmd_json = self._control_queue.get_nowait()
            except queue.Empty:
                break

            try:
                cmd = _json.loads(cmd_json)
            except _json.JSONDecodeError as e:
                from agent_console import warning
                warning(f"Control queue: invalid JSON: {e}")
                continue

            cmd_type = cmd.get("type", "")

            if cmd_type == "inject":
                # role is informational only (logged in status); always creates user message
                role = cmd.get("role", "user")
                content = cmd.get("content", "")
                if not content:
                    continue
                # Use bridge helper to maintain alternation (tool → assistant → user)
                self.context.append_synthetic_user_with_bridge("parent_inject", content)
                from agent_console import status
                status(f"Parent injected {role} message ({len(content)} chars)")

            elif cmd_type == "terminate":
                graceful = cmd.get("graceful", True)
                source = cmd.get("source", "parent")  # "parent" or "user"
                force_kill = cmd.get("force_kill", False)
                if force_kill:
                    # Immediate SIGKILL — flush audit first, then die.
                    # NOTE: SIGKILL is unrecoverable; no cleanup hooks fire.
                    from agent_audit_bridge import log_console_warning
                    _pid = os.getpid()
                    log_console_warning(
                        f"FORCE_KILL: received from {source}, pid={_pid}"
                    )
                    # Flush stdout/stderr so the audit line is actually written
                    import signal as _signal
                    import sys as _sys
                    _sys.stdout.flush()
                    _sys.stderr.flush()
                    os.kill(_pid, _signal.SIGKILL)
                elif graceful:
                    self.force_end_turn = "user_stop" if source == "user" else "parent_terminate_graceful"
                    if source == "parent":
                        # A2A parent: inject summary request
                        self.context.append_synthetic_user_with_bridge(
                            "parent_inject",
                            "Parent supervisor has terminated this task. "
                            "Please provide a final summary of your work.",
                        )
                        from agent_console import status
                        status("Parent requested graceful termination")
                    else:
                        # User steering: just end the turn
                        from agent_console import status
                        status("User requested stop — ending turn")
                else:
                    from agent_lifecycle import AgentLifecycle
                    AgentLifecycle.set_exit_requested(True)
                    from agent_console import status
                    status("Parent requested forceful termination")

            elif cmd_type == "redirect":
                new_task = cmd.get("task", "")
                if not new_task:
                    continue
                self.context.clear()
                self.context.append_user(new_task, user_type="redirect")
                self.loop_detector.reset()
                self._eot_protection.reset()
                self._cache_tracker.reset()
                # Clear stale state from previous task
                self._pending_a2a_responses.clear()
                self._pending_a2a_chunks.clear()
                self._current_a2a_request_id = None
                self._queued_images.clear()
                from agent_console import status
                status("Redirected to new task by parent")

            elif cmd_type == "status":
                from agent_audit_bridge import log_console_warning
                stats = self.loop_detector.get_stats()
                log_console_warning(
                    f"STATUS: context={len(self.context)}, "
                    f"loop_warnings={stats.get('total_warnings', 0)}, "
                    f"nesting={self.nesting_count}"
                )
            else:
                from agent_console import warning
                warning(f"Control queue: unknown command type '{cmd_type}'")

            processed += 1

        if processed > 0:
            from agent_audit_bridge import log_console_warning
            log_console_warning(f"Processed {processed} control commands")

    def _get_available_commands(self) -> dict[str, "CommandInfo"]:
        """Discover and return available markdown commands dynamically.

        Queries the command discovery system to retrieve all available
        markdown commands from the commands/ directory.
        Results are not cached to ensure fresh command list on each call.

        Returns:
            dict: Mapping of command names to CommandInfo objects.
        """
        from agent_command_registry import CommandSource

        return {
            cmd.name: cmd
            for cmd in CommandManager._get_registry().discover(CommandSource.MD)
        }

    def _handle_command(
        self, cmd_name: str, cmd_full: str, msg: Optional[InputMessage] = None
    ) -> None:
        """Dispatch a slash command to the appropriate handler.

        Delegates to CommandManager which resolves priority (PY > BUILTIN > MD)
        and dispatches to the correct source.
        """
        if cmd_full in ("", "/"):
            show_help()
            return

        if not CommandManager.dispatch(cmd_name, cmd_full, msg, self):
            unknown_command_error(cmd_name)

    def resolve_group_params(self) -> dict[str, Any]:
        """Return generation parameters for the current LLM group.

        Resolves generation parameters following a priority order from lowest to highest:
        1. Global inference_params (deprecated fallback from top-level "inference" block)
        2. Group-specific generation params (max_tokens, temperature, top_p, etc.)
        3. Group-specific chat_template_kwargs

        Returns:
            dict: Merged generation parameters with group-specific values taking
                precedence over global defaults.
        """
        group = self.llm_groups[self.current_group_name]
        params: dict[str, Any] = {}

        # 1) Global inference_params as base (deprecated fallback for configs
        #    that still use the top-level "inference" block).
        if self.inference_params:
            params.update(self.inference_params)

        # 2) Group-specific generation params override global values.
        for attr in (
            "max_tokens",
            "temperature",
            "top_p",
            "top_k",
            "min_p",
            "presence_penalty",
            "frequency_penalty",
            "repetition_penalty",
        ):
            val = getattr(group, attr, None)
            if val is not None:
                params[attr] = val

        # 3) Group-specific chat_template_kwargs override global values.
        if group.chat_template_kwargs:
            params["chat_template_kwargs"] = group.chat_template_kwargs

        return params

    def _rebuild_client(self, clear_overrides: bool = False) -> None:
        """Rebuild the HTTP client and refresh parameters after LLM group switch.

        Reinitializes the SimpleOpenAIClient with the current LLM group's
        configuration. Optionally clears any model/base URL/context overrides.

        Args:
            clear_overrides: If True, clears all LLM configuration overrides
                (_llm_model_override, _llm_base_url_override, _llm_context_override).
                If False, preserves existing overrides.

        Raises:
            ValueError: If the current LLM group is not found or has invalid config.
        """
        group = self.llm_groups.get(self.current_group_name)
        if not group:
            raise ValueError(
                f"No LLM group '{self.current_group_name}' found. "
                f"Available groups: {list(self.llm_groups.keys()) or '(none)'}"
            )
        if clear_overrides:
            self._llm_model_override = None
            self._llm_base_url_override = None
            self._llm_context_override = None

        base_url = self._llm_base_url_override or group.api_base
        if not base_url:
            raise ValueError(
                f"LLM group '{self.current_group_name}' has no valid api_base "
                f"(override={self._llm_base_url_override!r}, "
                f"group.api_base={group.api_base!r}). Cannot rebuild client."
            )

        self._current_api_key = group.api_key
        self.client = SimpleOpenAIClient(
            base_url=base_url,
            api_key=self._current_api_key,
            timeout=group.timeout,
            cache_tracker=self._cache_tracker,
        )
        self.model_name = self._llm_model_override or group.model
        self.base_url = self._llm_base_url_override or group.api_base
        self.max_tokens = group.max_tokens
        self.max_context_tokens = (
            self._llm_context_override
            if self._llm_context_override is not None
            else group.max_context_tokens
        )

        # Swap reflection scheduler if the new group has its own reflection config
        if group.reflection is not None:
            self.reflection_scheduler = ReflectionScheduler(group.reflection)
            self._loop_escalation.set_reflection_scheduler(self.reflection_scheduler)

    def _is_restricted_nesting(self) -> bool:
        """Check if current nesting type allows relaxed EOT (no sentinel required).

        Returns True for 'T' (think) and 'K' (skill) nesting types.
        These types accept a basic assistant message as end-of-turn without
        requiring the explicit sentinel confirmation.
        """
        return self.nesting_stack and self.nesting_stack[-1] in ("T", "K")

    def get_all_tools(self) -> list[dict]:
        """Return ALL tools in OpenAI function-calling format.

        Always returns the full tool list regardless of the tool filter.
        The tool filter is applied at execution time (agent_tool_executor
        line 219) where blocked tool calls are rejected with the denied message.

        CRITICAL: Never change the tool list sent to the LLM — this breaks
        prefix cache stability. The model always sees the same tools; the
        filter only blocks execution, not the API call.

        Returns:
            list[dict]: List of tool definitions in OpenAI format, each containing:
                - type: Always "function"
                - function: Dict with name, description, and parameters schema
        """
        all_tools = []
        for name in self.available_tool_names:
            tool_info = TOOLS.get(name)
            if not tool_info:
                continue
            schema = tool_info.get_schema()
            all_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": tool_info.description,
                        "parameters": schema
                        or {"type": "object", "properties": {}, "required": []},
                    },
                }
            )
        return all_tools

    def invoke_with_tools(self, user_input: str) -> str:
        """Send *user_input* to the model, execute any tool calls, return response text.

        CRITICAL OPENAI COMPLIANCE:
        This method APPENDS a user message to the context before calling the LLM.
        The context MUST end with an assistant or tool message before this call
        to maintain valid message alternation (no consecutive user messages).

        If the context already ends with a user message, use invoke_with_tools_loop()
        directly instead to avoid violating the OpenAI spec.

        Args:
            user_input: The user message content to append and send to the model.

        Returns:
            The final assistant response text (or error message).
        """
        self._turn_active = True
        try:
            self._session.audit_writer.user(user_input)
            if self.original_task is None:
                self.original_task = user_input
            self.context.append_user(user_input, user_type="real")
            result = self.invoke_with_tools_loop()
            self._session.audit_writer.flush()
            return result
        finally:
            self._turn_active = False

    def invoke_with_tools_loop(self) -> str:
        """Core loop: call LLM, execute tool calls, repeat until final response.

        CRITICAL OPENAI COMPLIANCE REQUIREMENT:
        The context MUST already end with a user message when this method is called.
        This method does NOT append any messages before the LLM call.

        Message alternation invariant maintained throughout:
          - After LLM returns tool_calls: assistant(tool_calls) -> tool results -> loop
          - After LLM returns plain text: potential EOT -> confirmation -> accept or rewind
          - After forced end-of-turn: assistant(force_end_turn) -> turn complete

        Accidental EOT protection:
          When the LLM returns plain text without tool calls, we inject a synthetic
          user message asking for confirmation. The LLM must reply with the sentinel
          string (ENDOFTURN) to confirm, or continue with tool calls. If the budget
          (_ACCIDENTAL_EOT_BUDGET) is exhausted, the turn is force-closed.

        This method is safe to call when the context ends with:
          - A user message (normal entry point)
          - A tool message (after tool execution, looping back to LLM)

        Do NOT call this if the context ends with an assistant message, as that
        would indicate an incomplete turn that should be closed first.

        Returns:
            The final assistant response text (or error message).
        """
        return run_loop(self)

    def run(
        self,
        inputs: list[str] = None,
        a2a_server=None,
        keep_alive=False,
        interactive=True,
    ) -> None:
        """Delegate the main run loop to InputHandler.

        Starts the agent's main execution loop by delegating to the InputHandler
        which manages user input processing, command handling, and interaction flow.

        Args:
            inputs: Optional list of initial input strings to process.
            a2a_server: Optional A2A (Agent-to-Agent) server instance.
            keep_alive: If True, keep the agent running after processing inputs.
            interactive: If True, enable interactive mode for user input.
        """
        InputHandler(self).run(
            inputs=inputs,
            a2a_server=a2a_server,
            keep_alive=keep_alive,
            interactive=interactive,
        )

    def _exec_tool(self, args: str) -> None:
        """Execute a tool directly from a command line.

        Parses and executes a tool with the given arguments in key=value format.
        This is used by the /exec command to run tools interactively.

        Args:
            args: Space-separated arguments in the format:
                "toolname arg1=val1 arg2=val2 ..."
                Example: "cd path=.." or "search query=python"

        Displays:
            - Usage message if no arguments provided
            - Error if tool not found
            - Error if tool has no run function
            - Tool result or error message
        """
        if not args:
            exec_usage()
            return

        parts = args.split()
        if not parts:
            exec_usage()
            return

        tool_name = parts[0]
        tool_args = {}
        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
                    value = int(value)
                elif value.replace(".", "").replace("-", "").isdigit():
                    try:
                        value = float(value)
                    except ValueError:
                        # Keep original string if float conversion fails
                        pass
                tool_args[key] = value

        tool_info = TOOLS.get(tool_name)
        if not tool_info:
            unknown_tool_error(tool_name)
            return
        tool_func = tool_info.run
        if not tool_func:
            no_run_function_error(tool_name)
            return

        tool_args["_ctx"] = ToolContext(agent=self, tool_call_id="0")

        # Fill optional parameter defaults from the tool's Args dataclass.
        # This must happen AFTER tool resolution so that alias-resolved canonical
        # argument names match the dataclass field names.
        tool_module = tool_info.module
        if tool_module is not None and hasattr(tool_module, "Args"):
            from tools.validation import fill_defaults_from_args
            fill_defaults_from_args(tool_args, tool_module)

        try:
            result = tool_func(**tool_args) if tool_args else tool_func()
            assistant_message_display(result)
        except (TypeError, KeyError, RuntimeError) as e:
            exec_tool_fail(str(e))

    def get_status(self) -> AgentStatus:
        """Return an encapsulated view of agent status for display functions.

        Replaces direct access to agent internals from the display layer.
        """
        token_count, percentage, byte_count, is_exact = self.context.get_usage_stats(
            self.max_context_tokens, self._session.last_exact_context_tokens
        )

        pending = None
        if self.context.is_tool_pending():
            pending = self.context.get_pending_tool_ids()

        return AgentStatus(
            # Context stats
            token_count=token_count,
            percentage=percentage,
            byte_count=byte_count,
            is_exact=is_exact,
            context_len=len(self.context),
            max_context_tokens=self.max_context_tokens,
            # Pending tools
            pending_tool_ids=pending,
            # Model info
            model_name=self.model_name,
            base_url=self.base_url,
            model_source="cli" if self._llm_model_override else f"group:{self.current_group_name}",
            base_url_source="cli" if self._llm_base_url_override else f"group:{self.current_group_name}",
            # Group info
            current_group_name=self.current_group_name,
            llm_groups=list(self.llm_groups.keys()),
            gen_params=self.resolve_group_params(),
            # Token tracking
            last_turn_in=self._session.last_turn_input_tokens,
            last_turn_out=self._session.last_turn_output_tokens,
            last_turn_cached=self._session.last_turn_cached_tokens,
            session_in=self._session.input_tokens,
            session_out=self._session.output_tokens,
            session_cached=self._session.cached_tokens,
            session_in_bytes=self._session.input_bytes,
            session_out_bytes=self._session.output_bytes,
            session_cached_bytes=self._session.cached_bytes,
            # Cache
            has_cache_data=self._session.cache_tracker.has_cache_data,
            cumulative_hit_rate=self._session.cache_tracker.cumulative_hit_rate,
            sliding_hit_rate=self._session.cache_tracker.sliding_hit_rate,
            last_hit_rate=self._session.cache_tracker.last_hit_rate,
            call_count=self._session.cache_tracker.call_count,
            # Agent info
            agent_name=self.agent_name,
            context_file=str(self._session.context_file),
            nesting_count=self.nesting_count,
            nesting_stack=self.nesting_stack,
            turn_active=self._turn_active,
            # Loop detection
            loop_stats=self.loop_detector.get_stats(),
            # Commands
            available_commands=list(self._get_available_commands().keys()),
        )

    # ── Backward-compatible property wrappers (tests access these directly) ──

    @property
    def nesting_count(self) -> int:
        """Nesting depth derived from nesting_stack length."""
        return len(self.nesting_stack)

    @property
    def audit_file(self) -> Path:
        """Delegate to session manager."""
        return self._session.audit_file

    @property
    def context_file(self) -> Path:
        """Delegate to session manager."""
        return self._session.context_file

    @context_file.setter
    def context_file(self, value: Path) -> None:
        self._session.context_file = value

    @property
    def audit_writer(self) -> AuditWriter:
        """Delegate to session manager."""
        return self._session.audit_writer
