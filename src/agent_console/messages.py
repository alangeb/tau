"""Console message templates and registry for TauErgon.

Provides the ``_ConsoleMessage`` class for creating simple, single-line
message templates. Each template handles display AND optional audit logging
in one call.

Also provides parameterized display helpers (``display_error``,
``display_warning``, etc.) that write text in a fixed color.

Centralized registry for all console messages. Provides a clean interface
for message registration, lookup, and bulk operations. All message
definitions are registered here and exposed as module-level attributes
for backward compatibility.

Boundary rules:
 - Simple single-line messages → ``_ConsoleMessage`` templates (this module)
 - Multi-line output, loops, conditional display → ``agent_console/`` submodules
 - Low-level primitives (``_cw``, ``echo``, etc.) → ``agent_console.primitives``
"""
from __future__ import annotations

import sys
from typing import Callable, Literal

from agent_models import Colors

from agent_console.audit import _log_audit
from agent_console.primitives import _cw


__all__ = [
    # Display helpers
    "display_error",
    "display_warning",
    "display_success",
    "display_info",
    "display_synthetic",
    # Template system
    "_ConsoleMessage",
    "_msg",
    # Registry
    "MessageRegistry",
    "register",
    "get_registry",
    "register_console_messages",
    # Error display
    "error", "warning", "invalid_mode_error",
    "unknown_command_error", "unknown_tool_error", "no_run_function_error",
    "command_file_not_found", "log_dir_error", "exec_tool_fail",
    "dynamic_command_result",
    # Message display
    "user_echo", "assistant_message_display", "user_message_display",
    # Flow control
    "restart_flow_info", "restart_flow_success", "restart_failure",
    "restart_fallback_failure", "force_exit_message", "interrupted_message",
    # Loop warnings
    "loop_warning_display",
    # Synthetic/injected messages
    "synthetic_user", "synthetic_assistant", "synthetic_bridge",
    # Subagent/fork
    "subagent_start_display", "fork_display",
    "subagent_output_footer",
    "subagent_error", "fork_error",
    # A2A/agent
    "agents_json", "agent_card_json", "agent_status_message",
    "a2a_cli_error", "a2a_started_message", "agent_a2a_response",
    # Compression
    "compress_success", "compress_fail",
    # Context display
    "context_cleared_success", "context_restored",
    "context_restore_failure", "no_context_file_found",
    # Tool display
    "tool_result", "no_tools_message", "shell_tool_not_available",
    "shell_command_usage", "tools_loaded_message", "tool_blocked",
    "exec_usage",
]


# ── Parameterized display helpers ──────────────────────────────────────────
# These replace thin wrapper functions. Used by agent_console/*.py.
# Each helper writes *text* in a fixed color.
#
# The helpers are generated via a factory to avoid repeating the same
# one-line ``_cw(color, text)`` boilerplate. New display helpers can be
# added by a single assignment below.


def _make_displayer(color: str, name: str, doc: str):
    """Create a display helper that writes *text* in *color*.

    Returns a function named *name* with a docstring of *doc*, so it
    behaves identically to an explicit ``def`` for introspection and
    debugging purposes.
    """
    def display(text: str) -> None:
        _cw(color, text)
    display.__name__ = name
    display.__qualname__ = name
    display.__doc__ = doc
    return display


display_error = _make_displayer(Colors.RED, "display_error", "Display an error message in red.")
display_warning = _make_displayer(Colors.YELLOW, "display_warning", "Display a warning message in yellow.")
display_success = _make_displayer(Colors.GREEN, "display_success", "Display a success message in green.")
display_info = _make_displayer(Colors.CYAN, "display_info", "Display an informational message in cyan.")
display_synthetic = _make_displayer(Colors.WHITE, "display_synthetic", "Display a synthetic/injected message in white.")


# ── Declarative Message Template ─────────────────────────────────────────────


class _ConsoleMessage:
    """Declarative message template that generates a callable display function.

    Replaces thin wrapper functions like:
        def unknown_command_error(cmd_name: str) -> None:
            display_error(f"Unknown command: /{cmd_name}")

    With registry entries:
        unknown_command_error = _msg("error", "Unknown command: /{cmd_name}")

    The optional *audit_level* parameter allows the audit log level to differ
    from the display level (e.g., display as error but log as warning).
    """
    __slots__ = ("_level", "_template", "_audit", "_audit_level", "_writer")

    def __init__(
        self,
        level: Literal["error", "warning", "success", "info"],
        template: str,
        *,
        audit: bool = False,
        audit_level: str | None = None,
        writer: Callable[[str], None] | None = None,
    ) -> None:
        self._level = level
        self._template = template
        self._audit = audit
        self._audit_level = audit_level
        self._writer = writer

    def __call__(self, *args, **kwargs) -> None:
        msg = self._template.format(*args, **kwargs)
        if self._writer is not None:
            self._writer(msg)
        elif self._level == "error":
            display_error(msg)
        elif self._level == "warning":
            display_warning(msg)
        elif self._level == "success":
            display_success(msg)
        elif self._level == "info":
            display_info(msg)
        else:
            display_info(msg)
        if self._audit:
            _log_audit(self._audit_level or self._level, msg)


def _msg(
    level: Literal["error", "warning", "success", "info"],
    template: str,
    *,
    audit: bool = False,
    audit_level: str | None = None,
    writer: Callable[[str], None] | None = None,
) -> _ConsoleMessage:
    """Create a console message template.

    Args:
        level: Display level ("error", "warning", "success", "info").
        template: Message template string with {} placeholders.
        audit: If True, also log to audit.
        audit_level: Override audit log level (defaults to *level*).
        writer: Custom writer function (bypasses standard display).
    """
    return _ConsoleMessage(level, template, audit=audit, audit_level=audit_level, writer=writer)


# ── Message Registry ────────────────────────────────────────────────────────


class MessageRegistry:
    """Centralized registry for all console messages.

    Provides a clean interface for message registration, lookup, and
    bulk operations. All message definitions are registered here and
    exposed as module-level attributes for backward compatibility.
    """
    __slots__ = ("_registry",)

    def __init__(self) -> None:
        self._registry: dict[str, _ConsoleMessage] = {}

    def register(
        self,
        name: str,
        level: Literal["error", "warning", "success", "info"],
        template: str,
        *,
        audit: bool = False,
        audit_level: str | None = None,
        writer: Callable[[str], None] | None = None,
    ) -> _ConsoleMessage:
        """Register a message template and return the callable."""
        msg = _ConsoleMessage(level, template, audit=audit, audit_level=audit_level, writer=writer)
        self._registry[name] = msg
        return msg

    def get(self, name: str) -> _ConsoleMessage | None:
        """Look up a registered message by name."""
        return self._registry.get(name)

    def get_all(self) -> dict[str, _ConsoleMessage]:
        """Return all registered messages."""
        return dict(self._registry)

    def names(self) -> list[str]:
        """Return sorted list of registered message names."""
        return sorted(self._registry.keys())


# Singleton registry instance
_registry = MessageRegistry()


# ── Message Definitions ──────────────────────────────────────────────────────

# Error display (all errors logged to audit)
error = _registry.register("error", "error", "{}", audit=True)
warning = _registry.register("warning", "warning", "{}", audit=True)
invalid_mode_error = _registry.register("invalid_mode_error", "error", "Invalid mode '{}'. Valid modes: {}", audit=True)
unknown_command_error = _registry.register("unknown_command_error", "error", "Unknown command: /{}", audit=True)
unknown_tool_error = _registry.register("unknown_tool_error", "error", "Unknown tool: {}", audit=True)
no_run_function_error = _registry.register("no_run_function_error", "error", "Tool has no run function: {}", audit=True)
command_file_not_found = _registry.register("command_file_not_found", "error", "Command file not found: {}", audit=True)
log_dir_error = _registry.register("log_dir_error", "error", "ERROR: Cannot create log directory {}: {}", audit=True)
exec_tool_fail = _registry.register("exec_tool_fail", "error", "Error executing tool: {}", audit=True)
dynamic_command_result = _registry.register("dynamic_command_result", "success", "{}", audit=True)

# Message display
user_echo = _registry.register("user_echo", "info", ">>> {}", writer=lambda t: sys.stdout.write(f"{t}\n"))
assistant_message_display = _registry.register("assistant_message_display", "success", "[ASSISTANT] {}")
user_message_display = _registry.register("user_message_display", "info", "[USER] {}", writer=lambda t: sys.stdout.write(f"{t}\n"))

# Flow control (all logged to audit)
restart_flow_info = _registry.register("restart_flow_info", "info", "[Restarting agent...] Command: {}", audit=True)
restart_flow_success = _registry.register("restart_flow_success", "success", "Exiting current agent...", audit=True)
restart_failure = _registry.register("restart_failure", "error", "Failed to restart agent: {}", audit=True)
restart_fallback_failure = _registry.register("restart_fallback_failure", "error", "Fallback also failed: {}", audit=True)
force_exit_message = _registry.register("force_exit_message", "info", "\n\nForced exit requested. Cleaning up...", audit=True)
interrupted_message = _registry.register("interrupted_message", "info", "\n\nInterrupted. Press Ctrl+C again to force exit.", audit=True)

# Loop warnings
loop_warning_display = _registry.register("loop_warning_display", "warning", "{}", audit=True)

# Synthetic/injected messages (white color, logged to audit)
synthetic_user = _registry.register("synthetic_user", "info", "[SYNTHETIC USER: {}] {}", audit=True, writer=lambda t: display_synthetic(t))
synthetic_assistant = _registry.register("synthetic_assistant", "info", "[SYNTHETIC ASSISTANT] {}", audit=True, writer=lambda t: display_synthetic(t))
synthetic_bridge = _registry.register("synthetic_bridge", "info", "[SYNTHETIC BRIDGE: {}] {}", audit=True, writer=lambda t: display_synthetic(t))

# Subagent/fork (all logged to audit)
subagent_start_display = _registry.register("subagent_start_display", "info", "[Starting subagent for: {}...]", audit=True)
fork_display = _registry.register("fork_display", "info", "/fork {}", audit=True)
subagent_output_footer = _registry.register("subagent_output_footer", "info", "[End of subagent output]", audit=True)
subagent_error = _registry.register("subagent_error", "error", "Subagent error: {}", audit=True)
fork_error = _registry.register("fork_error", "error", "Fork error: {}", audit=True)

# A2A/agent (all logged to audit)
agents_json = _registry.register("agents_json", "info", "{}", audit=True)
agent_card_json = _registry.register("agent_card_json", "info", "{}", audit=True, writer=lambda t: sys.stdout.write(t + "\n"))
agent_status_message = _registry.register("agent_status_message", "warning", "{}", audit=True)
a2a_cli_error = _registry.register("a2a_cli_error", "error", "{}", audit=True)
a2a_started_message = _registry.register("a2a_started_message", "info", "[A2A server started: {}]", audit=True)
agent_a2a_response = _registry.register("agent_a2a_response", "info", "[{}]", audit=True, writer=lambda t: sys.stdout.write(f"{t}\n"))

# Compression (all logged to audit)
compress_success = _registry.register("compress_success", "success", "[COMPRESS] Compression successful.", audit=True)
compress_fail = _registry.register("compress_fail", "error", "[COMPRESS] Compression failed.", audit=True)

# Context display (all logged to audit)
context_cleared_success = _registry.register("context_cleared_success", "info", "Context cleared.", audit=True)
context_restored = _registry.register("context_restored", "info", "[Context restored: {} messages from {}]", audit=True)
context_restore_failure = _registry.register("context_restore_failure", "error", "[Context file empty/malformed: {}]", audit=True, audit_level="warning")
no_context_file_found = _registry.register("no_context_file_found", "error", "[No context file found for this session]", audit=True, audit_level="warning")

# Tool display (all logged to audit)
tool_result = _registry.register("tool_result", "info", "{}", audit=True)
no_tools_message = _registry.register("no_tools_message", "warning", "No tools available.", audit=True)
shell_tool_not_available = _registry.register("shell_tool_not_available", "error", "Tool 'bash' not available.", audit=True)
shell_command_usage = _registry.register("shell_command_usage", "info", "Usage: ! <command>", audit=True)
tools_loaded_message = _registry.register("tools_loaded_message", "info", "[Loaded {} tools]", audit=True)
tool_blocked = _registry.register("tool_blocked", "warning", "Tool '{}' is blocked. Available: {}", audit=True)

# exec_usage: static message, no args
exec_usage = _registry.register("exec_usage", "info", "Usage: /exec toolname arg1=val1 arg2=val2 ...", audit=True)


# ── Registry helpers ─────────────────────────────────────────────────────────


def register(name: str, level: Literal["error", "warning", "success", "info"], template: str, **kwargs) -> _ConsoleMessage:
    """Register a message with the global registry and return the callable.

    This is a convenience wrapper around ``MessageRegistry.register()`` that
    also exposes the message as a module-level attribute for backward compatibility.
    """
    msg = _registry.register(name, level, template, **kwargs)
    # Expose as module-level attribute
    globals()[name] = msg
    return msg


def get_registry() -> MessageRegistry:
    """Return the global message registry instance."""
    return _registry


def register_console_messages() -> None:
    """Register console message callbacks with the audit bridge.

    Call this once during agent initialization to wire up the warning
    callback for ``agent_session`` console warnings.
    """
    from agent_audit_bridge import register_console_warning_callback
    register_console_warning_callback(warning)
