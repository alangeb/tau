"""Consolidated display functions for TauErgon console.

Merged from: tool_display, command_display, status_display, context_display,
llm_display, simple_display, loop_warning.

All simple single-line messages should use the MessageRegistry in
``agent_console.messages``. Complex multi-line formatting stays here.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path

from agent_console.audit import _log_audit
from agent_console.primitives import _cw
from agent_console.primitives import (
    _role_color,
    blank_line,
    compute_duration,
    echo,
    format_duration_ms,
)
from agent_console.messages import (
    display_error,
    display_info,
    display_success,
    display_warning,
    get_registry,
)

_registry = get_registry()

__all__ = [
    # Tool display
    "tool_start",
    "tool_output",
    "tool_error_detail",
    "tools_listing",
    "tools_json_schema",
    "agents_table_header",
    "agents_table_row",
    # Command display
    "help_display",
    "show_help",
    "show_commands",
    "show_tools",
    "show_tools_json",
    "show_command_help",
    "show_agent_card",
    # Status display
    "agent_status",
    "exit_summary",
    "print_agent_exit_summary",
    "print_context_status",
    "build_cache_hit_rates_str",
    # Context display
    "context_dump",
    "context_summary_stats",
    "context_status_bar",
    "context_validation_warning",
    "context_append_warning",
    "context_list_display",
    "context_preview_display",
    "context_validation_display",
    "context_dump_with_json",
    # LLM display
    "llm_timeout_message",
    "llm_validation_retry",
    "compression_step_summary",
    # Simple display
    "error_display",
    "undo_message",
    "restart_flow",
    "subagent_usage",
    "fork_usage",
    "subagent_output_header",
    # Loop warning
    "loop_warning",
]


# ── Tool Display ──────────────────────────────────────────────────────────────


def tool_start(name: str, args_str: str) -> None:
    fmt = f"\u23e4 {name}({args_str})" if args_str else f"\u23e4 {name}()"
    display_info(fmt)


def tool_output(output: str, _tool_name: str) -> None:
    if not isinstance(output, str):
        return
    output_str = output[:500] + "..." if len(output) > 500 else output
    all_lines = output_str.split("\n")
    line_count = len(all_lines)
    display_info(f"+--- total {line_count} lines---+")
    for line in all_lines[:20]:
        if line:
            display_info(f"| {line[:132]}")
    if line_count > 20:
        display_info(f"| ... ({line_count - 20} more lines)")
    display_info("+--- end ---+")


def tool_error_detail(
    tool_name: str,
    tc: dict,
    error: BaseException | None = None,
    duration_ms: float | None = None,
) -> None:
    sep = "=" * 60
    display_error(sep)
    display_error(f"ERROR invoking tool '{tool_name}':")

    # Show error type and message
    if error is not None:
        error_type = type(error).__name__
        error_msg = str(error)
        display_error(f"Error type: {error_type}")
        if error_msg:
            display_error(f"Error message: {error_msg}")

    # Show duration if available
    if duration_ms is not None:
        display_error(f"Duration: {format_duration_ms(duration_ms)}")

    # Show complete tool call (without args_dict which can be huge)
    tc_clean = {k: v for k, v in tc.items() if k != "args_dict"}
    display_error(f"Complete tool call: {json.dumps(tc_clean)}")
    display_error(sep)


def tools_listing(tool_count: int, tool_data: list[dict]) -> None:
    display_info(f"AVAILABLE TOOLS ({tool_count})")
    for t in tool_data:
        display_success(f"{t['name']}: {t['short_desc']}{t['args_info']}")
    sys.stdout.write("\n")


def tools_json_schema(tool_count: int, tools_json: str) -> None:
    sys.stdout.write(tools_json + "\n")


def agents_table_header() -> None:
    header = f"{'PID':<6} {'Status':<10} {'Tools':<6} {'Model':<25} {'Name':<15} {'Working Dir':<35}"
    display_info(header)
    display_info("-" * 105)


def agents_table_row(agent: dict) -> None:
    row = (
        f"{agent['pid']:<6} "
        f"{agent['status']:<10} "
        f"{agent.get('tools_count', 'N/A'):<6} "
        f"{agent.get('model', 'N/A'):<25} "
        f"{agent.get('name', 'Unknown'):<15} "
        f"{agent.get('working_dir', 'N/A'):<35}"
    )
    display_info(row)


# ── Command Display ───────────────────────────────────────────────────────────


def help_display(title: str, width: int, body: str) -> None:
    bar = "=" * width
    display_info(bar)
    display_info(title)
    display_info(bar)
    sys.stdout.write(body)


def show_help() -> None:
    """Display help information with all available commands."""
    from agent_command_handlers import BUILTIN_CMD_NAMES, get_primary_command_info
    from agent_commands import CommandManager
    from agent_command_registry import CommandSource

    width = 18  # Fixed column width for help display
    all_info = get_primary_command_info()
    registry = CommandManager._get_registry()
    py_cmds = registry.discover(CommandSource.PY)
    md_cmds = registry.discover(CommandSource.MD)

    base_text = "HELP\n\n"
    base_text += "\n".join(_format_builtin_section(all_info, None, width))
    base_text += "\n".join(_format_py_section(py_cmds, BUILTIN_CMD_NAMES, width))
    base_text += "\n".join(_format_md_section(md_cmds, width))
    base_text += "Input prefixes:\n"
    base_text += "  ! <command>        - Execute bash command\n"
    base_text += "\n"
    base_text += "  +message           - Turn steering (only during active turns):\n"
    base_text += "    +message         - Inject message into running turn\n"
    base_text += "    +stop            - End turn gracefully\n"
    base_text += "    +redirect task   - Clear context, start new task\n"
    base_text += "    +status          - Show diagnostics\n"
    base_text += "\n"
    base_text += "  #                  - Multiline block (supports #! or #+):\n"
    base_text += "    #!               - Start multiline block ('#!' continuation, blank lines end)\n"
    base_text += "    #+               - Turn steering from within multiline block (same as +)\n"

    help_display("HELP", 60, base_text)


def show_commands() -> None:
    """List all available commands including built-in and custom commands."""
    from agent_command_handlers import BUILTIN_CMD_NAMES, get_primary_command_info
    from agent_commands import CommandManager
    from agent_command_registry import CommandSource

    width = 0  # Variable width for commands display
    registry = CommandManager._get_registry()
    py_names = registry.get_names(CommandSource.PY)
    all_info = get_primary_command_info()
    py_cmds = registry.discover(CommandSource.PY)
    md_cmds = registry.discover(CommandSource.MD)

    lines: list[str] = ["AVAILABLE COMMANDS\n"]
    lines.extend(_format_builtin_section(all_info, py_names, width))
    lines.extend(_format_py_section(py_cmds, BUILTIN_CMD_NAMES, width, ""))
    lines.extend(_format_md_section(md_cmds, width, ""))

    echo("\n".join(lines), newline=False)


def show_tools() -> None:
    """Display available tools with descriptions and schema details."""
    from tools import TOOLS

    tools = list(TOOLS.values())
    if not tools:
        from agent_console.messages import no_tools_message
        no_tools_message()
        return

    tool_data = []
    for tool in sorted(tools, key=lambda t: t.name):
        name = tool.name
        desc = tool.description
        args_schema = getattr(tool.module, "Args", None)
        args_info = ""
        if args_schema:
            try:
                if hasattr(args_schema, "model_json_schema"):
                    schema = args_schema.model_json_schema()
                else:
                    schema = args_schema
                properties = schema.get("properties", {})
                required = schema.get("required", [])
                if properties:
                    required_fields = [f for f in required if f in properties]
                    optional_fields = [f for f in properties if f not in required]
                    args_info = f" [required: {', '.join(required_fields) if required_fields else 'none'}, optional: {', '.join(optional_fields) if optional_fields else 'none'}]"
            except (TypeError, KeyError, AttributeError):
                pass
        short_desc = desc[:60] + "..." if len(desc) > 60 else desc
        tool_data.append(
            {"name": name, "short_desc": short_desc, "args_info": args_info}
        )
    tools_listing(len(tools), tool_data)


def show_tools_json() -> None:
    """Display all tools as JSON with full schema details."""
    from tools import TOOLS
    from tools.validation import _dataclass_to_json_schema

    serializable_tools = {}
    for name, tool in TOOLS.items():
        tool_dict = tool.to_dict()
        serializable_tool = {}
        for key, value in tool_dict.items():
            if key == "args_schema" and value is not None:
                try:
                    if hasattr(value, "model_json_schema"):
                        serializable_tool[key] = value.model_json_schema()
                    else:
                        serializable_tool[key] = _dataclass_to_json_schema(value)
                except (TypeError, KeyError, AttributeError):
                    serializable_tool[key] = str(value)
                continue
            if callable(value):
                continue
            if isinstance(value, bytes):
                continue
            serializable_tool[key] = value
        serializable_tools[name] = serializable_tool

    tools_json_schema(
        len(serializable_tools), json.dumps(serializable_tools, indent=2)
    )


def show_command_help(cmd_name: str) -> None:
    """Display help for a specific command.

    Shows usage for commands that have subcommands. Works for both builtin
    and external Python commands.
    """
    from agent_command_handlers import get_command_info

    info = get_command_info(cmd_name)
    if info is None:
        # Not a builtin — check if it's an external command with known subcommands
        # For external commands, we rely on the command's own help output
        return

    primary, aliases, desc, subcmds = info
    if not subcmds:
        # No subcommands declared — nothing to show
        return

    title = f"/{primary} USAGE"
    lines = [f"{title}\n"]
    if aliases:
        lines.append(f"  Aliases: {', '.join(f'/{a}' for a in aliases)}")
    lines.append(f"  Description: {desc}")
    lines.append(f"  Subcommands: {', '.join(subcmds)}")
    lines.append("")
    lines.append("  Use /cmd help or /cmd -h to show this message.\n")

    help_display(title, 60, "\n".join(lines))


def show_agent_card(status: object) -> dict:
    """Generate and return the agent card as a dictionary."""
    from tools import TOOLS

    agent_card = {
        "name": status.agent_name,
        "description": "A helpful AI assistant with access to tools, skills, and commands",
        "url": status.base_url,
        "model": status.model_name,
        "capabilities": {
            "tools": list(TOOLS.keys()),
            "skills": ["skill"],
            "commands": status.available_commands,
        },
        "context": {
            "messages": status.context_len,
            "tokens": status.token_count,
            "bytes": status.byte_count,
            "max_tokens": status.max_context_tokens,
            "is_exact": status.is_exact,
        },
    }
    return agent_card


# ── Shared command formatting helpers ────────────────────────────────────────


def _subcmd_hint(subcmds: tuple[str, ...]) -> str:
    """Format subcommand hint for display."""
    return f" [{', '.join(subcmds)}]" if subcmds else ""


def _override_text(name: str, builtin_names: frozenset[str], text: str) -> str:
    """Return *text* if *name* overrides a builtin, else empty string."""
    return text if name in builtin_names else ""


# Canonical override badge text — used by both show_help and show_commands.
_OVERRIDE_BADGE = " (overrides builtin)"


def _format_builtin_entry(primary: str, entry: tuple, width: int) -> str:
    """Format a single builtin command entry."""
    desc = entry[2]  # description
    subcmds = entry[3]  # subcommands
    hint = _subcmd_hint(subcmds)
    if width > 0:
        return f"  /{primary:<{width}} - {desc}{hint}"
    return f"  /{primary}  -  {desc}{hint}" if desc else f"  /{primary}{hint}"


def _format_py_section(py_cmds: list, builtin_names: frozenset[str], width: int,
                        default_desc: str = "No description") -> list[str]:
    """Format the external Python commands section."""
    lines: list[str] = []
    if not py_cmds:
        lines.append("  (no external python commands found)")
        return lines
    lines.append("External Python Commands:")
    for cmd in sorted(py_cmds, key=lambda c: c.name):
        name = cmd.name
        desc = cmd.description or default_desc
        subcmds = cmd.subcommands
        hint = _subcmd_hint(subcmds)
        override = _override_text(name, builtin_names, _OVERRIDE_BADGE)
        if width > 0:
            lines.append(f"  /{name:<{width}} - {desc}{hint}{override}")
        else:
            lines.append(f"  /{name}  -  {desc}{hint}{override}")
    lines.append("")
    return lines


def _format_md_section(md_cmds: list, width: int,
                        default_desc: str = "No description") -> list[str]:
    """Format the external Markdown commands section."""
    lines: list[str] = []
    if not md_cmds:
        lines.append("  (no external markdown commands found)")
        return lines
    lines.append("External Markdown Commands:")
    for cmd in sorted(md_cmds, key=lambda c: c.name):
        name = cmd.name
        desc = cmd.description or default_desc
        if width > 0:
            lines.append(f"  /{name:<{width}} - {desc}")
        else:
            lines.append(f"  /{name}  -  {desc}")
    lines.append("")
    return lines


def _format_builtin_section(all_info: dict, py_names: set[str] | None, width: int) -> list[str]:
    """Format the built-in commands section.

    If *py_names* is provided, skip builtins that are overridden by py commands.
    """
    lines: list[str] = ["Built-in Commands:"]
    for primary in sorted(all_info.keys()):
        if py_names and primary in py_names:
            continue
        lines.append(_format_builtin_entry(primary, all_info[primary], width))
    lines.append("")
    lines.append("  Tip: /cmd help or /cmd -h shows usage for commands with subcommands.")
    lines.append("")
    return lines


# ── Status Display ────────────────────────────────────────────────────────────


def agent_status(status: object) -> None:
    """Display comprehensive agent status information."""
    from agent_console.messages import display_success

    token_display = (
        f"{status.token_count:,}" if status.is_exact else f"~{status.token_count:,}"
    )

    display_info("AGENT STATUS")
    display_success(f"PID: {os.getpid()}")
    display_success(f"Parent PID: {os.getppid()}")
    if status.agent_name:
        display_success(f"Name: {status.agent_name}")
    display_success(f"Context: {status.context_len} msgs | {token_display} tokens ({status.byte_count:,} bytes)")
    display_success(f"Capacity: {status.percentage * 100:.1f}% ({status.max_context_tokens:,} max)")
    display_success(f"Session file: {status.context_file}")
    if status.current_group_name:
        groups = f" (available: {', '.join(status.llm_groups)})" if status.llm_groups else ""
        display_success(f"LLM group: {status.current_group_name}{groups}")
    model_src = f" [{status.model_source}]" if status.model_source else ""
    display_success(f"Model: {status.model_name}{model_src}")
    api_src = f" [{status.base_url_source}]" if status.base_url_source else ""
    display_success(f"API: {status.base_url}{api_src}")
    if status.gen_params:
        formatted = ", ".join(f"{k}={v}" for k, v in status.gen_params.items())
        display_success(f"Gen params: {formatted}")
    if status.pending_tool_ids:
        display_success(f"\u26a0 Pending tool calls: {status.pending_tool_ids}")
    display_success(f"Working directory: {Path.cwd()}")
    if status.last_turn_in > 0:
        display_success(f"Last turn tokens: {status.last_turn_in:,} in + {status.last_turn_out:,} out + {status.last_turn_cached:,} cached")
    total = status.session_in + status.session_out
    total_bytes = status.session_in_bytes + status.session_out_bytes
    display_success(f"Session total: {status.session_in:,} in + {status.session_out:,} out + {status.session_cached:,} cached = {total:,} total")
    display_success(f"Session bytes: {status.session_in_bytes:,} in + {status.session_out_bytes:,} out + {status.session_cached_bytes:,} cached = {total_bytes:,} total")
    if status.has_cache_data:
        display_success(f"Cache hit rates: {build_cache_hit_rates_str(status)}")
    blank_line()


def exit_summary(status: object, duration: float, tool_count: int) -> None:
    """Print a tidy exit summary with context metrics and session information."""
    from agent_console.primitives import _cw
    from agent_models import Colors

    loop_stats = status.loop_stats or {}
    entropy = loop_stats.get("entropy", 0.0)
    history_size = loop_stats.get("history_size", 0)

    token_display = (
        f"{status.token_count:,}" if status.is_exact else f"~{status.token_count:,}"
    )

    cache_hit_rates = (
        build_cache_hit_rates_str(status) if status.has_cache_data else None
    )

    blank_line()
    _cw(Colors.INVERT_CYAN, "########## EXIT SUMMARY ##########")
    display_info(f"Context: {status.context_len} msgs | {token_display} tokens ({status.byte_count:,} bytes)")
    display_info(f"Session file: {status.context_file}")
    display_info(f"Duration: {duration:.1f}s | Tools: {tool_count} | Entropy: {entropy:.2f} (history: {history_size})")
    total = status.session_in + status.session_out
    display_info(f"Token usage: {status.session_in:,} in + {status.session_out:,} out + {status.session_cached:,} cached = {total:,} total")
    if cache_hit_rates:
        display_info(f"Cache hit rates: {cache_hit_rates}")
    display_info("==================================")
    blank_line()


def print_agent_exit_summary(agent: object) -> None:
    """Print exit summary for an agent-like object."""
    duration = compute_duration(agent)
    tool_count = len(agent.available_tool_names)
    exit_summary(agent.get_status(), duration, tool_count)


def print_context_status(status: object) -> None:
    """Print a single-line context status display."""
    from agent_console.primitives import _cw
    from agent_models import Colors

    loop_stats = status.loop_stats or {}
    entropy = loop_stats.get("entropy", 0.0)
    history_size = loop_stats.get("history_size", 0)
    cwd = Path.cwd()
    try:
        cwd = "~/" + str(cwd.relative_to(Path.home()))
    except ValueError:
        cwd = str(cwd)

    token_display = f"{status.token_count}" if status.is_exact else f"~{status.token_count}"

    cache_str = (
        build_cache_hit_rates_str(status)
        if status.has_cache_data
        else ""
    )

    timestamp = datetime.datetime.now().strftime("%y%m%d %H%M%S")
    current_pid = os.getpid()
    parent_pid = os.getppid()
    base_content = (
        f"ctx: {token_display} tk ({status.percentage:.1%}) {status.context_len} msgs"
        + (f" | cache: {cache_str}%" if cache_str else "")
        + f" | pid: {current_pid}({parent_pid}) | {timestamp} | entropy: {entropy:.2f} ({history_size}) | cwd: {cwd}"
    )

    if status.nesting_stack:
        base_content += f" | nest: {status.nesting_stack}"
        color = Colors.INVERT_BLUE
    else:
        base_content += " | nest: ."
        color = Colors.INVERT_CYAN

    base_content += f" | llmg: {status.current_group_name}"
    base_content += f" | name: {status.agent_name}"

    _cw(color, f"# {base_content}")


def build_cache_hit_rates_str(status: object) -> str:
    """Build a cache hit rate display string, handling None values safely."""
    parts: list[str] = []
    cum = status.cumulative_hit_rate
    slid = status.sliding_hit_rate
    last = status.last_hit_rate
    if cum is not None:
        parts.append(f"{int(cum * 100)}%")
    if slid is not None:
        parts.append(f"{int(slid * 100)}%")
    if last is not None:
        parts.append(str(int(last * 100)))
    return "/".join(parts) if parts else ""


# ── Context Display ───────────────────────────────────────────────────────────


def context_dump(title: str, lines_data: list[dict]) -> None:
    from agent_models import Colors

    display_info(title)
    for item in lines_data:
        role = item["role"]
        content = item["content"]
        tool_info = item.get("tool_info", "")
        idx = item.get("index", 0)
        color = _role_color(role)
        sys.stdout.write(f"{color}{idx + 1}. [{role}]{tool_info} {color}{content}{Colors.RESET}\n")


def context_summary_stats(
    context_len: int,
    token_display: str,
    percentage: float,
    byte_count: int,
    max_tokens: int,
) -> None:
    display_info(f"CONTEXT SUMMARY ({context_len} messages)")
    display_success(f"Tokens: {token_display} ({percentage:.1%} of {max_tokens:,} max)")
    display_success(f"Bytes: {byte_count:,}")
    blank_line()


def context_status_bar(content: str, color: str | None = None) -> None:
    from agent_models import Colors
    _cw(color if color is not None else Colors.INVERT_CYAN, f"# {content}")


def context_validation_warning(error_lines: list[str]) -> None:
    sep = "=" * 60
    display_error(sep)
    display_error("\u26a0\ufe0f  CRITICAL CONTEXT VALIDATION WARNING")
    display_error(sep)
    for line in error_lines:
        display_error(f"  {line}")
    display_error(sep)
    # Audit: log the full warning block
    audit_lines = ["CRITICAL CONTEXT VALIDATION WARNING"]
    audit_lines.extend(error_lines)
    _log_audit("error", " | ".join(audit_lines))


def context_append_warning(errors: list[str]) -> None:
    display_error("\u26a0 Context validation warning:")
    for err in errors:
        display_error(f"  - {err}")
    # Audit: log each error
    for err in errors:
        _log_audit("warning", f"Context validation: {err}")


def context_list_display(contexts: list[dict]) -> None:
    if not contexts:
        display_warning("[No context files found]")
        return
    display_info("Available context files (use /continue <n> to load):")
    header = f"{'ID':<5}{'Age':<10}{'Msgs':<6}{'File':<45}Last User Message"
    display_info(header)
    sep = f"{'─'*4:<5}{'─'*9:<10}{'─'*5:<6}{'─'*44:<45}{'─'*40}"
    display_info(sep)
    for ctx in contexts:
        last_user = ctx.get("last_user", "") or "(no user message)"
        name = ctx['name']
        if len(name) > 42:
            name = name[:39] + "..."
        sys.stdout.write(
            f"{ctx['id']:<5}"
            f"{ctx['age']:<10}"
            f"{ctx['msg_count']:<6}"
            f"{name:<45}"
            f"{last_user}\n"
        )
    sys.stdout.write("\n")


def context_preview_display(context_file: str, messages: list[dict]) -> None:
    from agent_models import Colors

    if not messages:
        display_warning(f"[Preview empty or unreadable: {context_file}]")
        return
    display_info(f"Preview of {context_file} (last {len(messages)} messages):")
    display_info("─" * 60)
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, list):
            image_count = sum(1 for p in content if p.get("type") == "image_url")
            text_parts = [p.get("text", "") for p in content if p.get("type") == "text"]
            content = f"[{image_count} image(s)]"
            if text_parts:
                content += ": " + text_parts[0][:200]
        color = _role_color(role)
        sys.stdout.write(f"{color}[{role.upper()}] {content}{Colors.RESET}\n")
    sys.stdout.write("\n")


def context_validation_display(errors: list[str], context_len: int | None = None,
                                last_role: str | None = None) -> None:
    display_error("Context validation errors detected:")
    if context_len is not None or last_role is not None:
        display_error(f"  Context state: {context_len} messages, last role: {last_role}")
    for error in errors:
        display_error(f"  {error}")
    blank_line()
    # Audit: log context state and each error
    state = ""
    if context_len is not None and last_role is not None:
        state = f" ({context_len} msgs, last={last_role}): {len(errors)} error(s)"
    _log_audit("warning", f"Context validation{state}")
    for err in errors:
        _log_audit("warning", f"Context validation: {err}")


def context_dump_with_json(json_str: str) -> None:
    sys.stdout.write(json_str)


# ── LLM Display ──────────────────────────────────────────────────────────────


def llm_timeout_message(attempt: int, max_retries: int) -> None:
    remaining = max_retries - attempt - 1
    display_warning("[TIMEOUT]")
    display_warning(f"Request timed out after {attempt + 1} attempt(s)")
    display_warning(f"Retrying... ({remaining} attempt(s) remaining)")


def llm_validation_retry(attempt: int, max_retries: int, reason: str) -> None:
    truncated = reason[:120] + "..." if len(reason) > 120 else reason
    remaining = max_retries - attempt - 1
    display_warning(f"[VALIDATION RETRY {attempt + 1}/{max_retries}]")
    display_warning(truncated)
    display_warning(f"Retrying... ({remaining} attempt(s) remaining)")


def compression_step_summary(
    step_name: str,
    step_idx: int,
    total_steps: int,
    bytes_before: int,
    msgs_before: int,
    bytes_after: int,
    msgs_after: int,
    action_summary: str,
    status: str,
) -> None:
    """Emit a one-liner console summary for a compression pipeline step."""
    from agent_models import Colors

    arrow = f"{bytes_before:,} \u2192 {bytes_after:,} bytes, {msgs_before} \u2192 {msgs_after} msgs"
    status_tag = f" [{status}]" if status else ""
    _cw(
        Colors.BLUE,
        f"[COMPRESS] STEP {step_idx}/{total_steps} {step_name}: {arrow} | {action_summary}{status_tag}",
    )


# ── Simple Display ───────────────────────────────────────────────────────────


def error_display(label: str, detail: str) -> None:
    display_error(f"[{label}]")
    sys.stdout.write(f"{detail}\n")


def undo_message(removed: int) -> None:
    if removed == 0:
        display_warning("Undid 0 message(s). Nothing to undo.")
    else:
        display_info(f"Undid {removed} message(s). Context now ends before last user input.")


def restart_flow(command_args: str) -> None:
    from agent_console.messages import restart_flow_info, restart_flow_success
    restart_flow_info(command_args)
    restart_flow_success()


def subagent_usage() -> None:
    """Display usage instructions for the /subagent command."""
    display_info("Usage: /subagent <task>")
    display_info("Example: /subagent Search for latest Python typing features")


def fork_usage() -> None:
    """Display usage instructions for the /fork command."""
    display_info("Usage: /fork <task>")
    display_info("Example: /fork Continue our discussion about Python typing")


def subagent_output_header() -> None:
    """Display the header for subagent output."""
    display_info("[Subagent output:")
    blank_line()


# ── Loop Warning ─────────────────────────────────────────────────────────────


def loop_warning(level: int, message: str) -> None:
    """Display a loop warning with level-appropriate emoji and color."""
    from agent_models import Colors

    if not 1 <= level <= 4:
        raise ValueError(
            f"loop_warning: level must be 1-4, got {level}"
        )
    _cw(Colors.YELLOW if level == 1 else Colors.RED,
        ("", "\u26a0\ufe0f  ", "\U0001f534 ", "\U0001f6a8 ", "\U0001f4a5 ")[level] + message)