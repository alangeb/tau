"""Command display functions for TauErgon console.

Handles help display, command listings, tool listings, and agent card display.
"""
from __future__ import annotations

import json
import sys

from agent_console.primitives import (
    display_info,
    echo,
)

__all__ = [
    "help_display",
    "show_help",
    "show_commands",
    "show_tools",
    "show_tools_json",
    "show_command_help",
    "show_agent_card",
]


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

    width = 18
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

    width = 0
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
        from agent_console.templates import no_tools_message
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
    from agent_console.display_tool import tools_listing
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

    from agent_console.display_tool import tools_json_schema
    tools_json_schema(
        len(serializable_tools), json.dumps(serializable_tools, indent=2)
    )


def show_command_help(cmd_name: str) -> None:
    """Display help for a specific command."""
    from agent_command_handlers import get_command_info

    info = get_command_info(cmd_name)
    if info is None:
        return

    primary, aliases, desc, subcmds = info
    if not subcmds:
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


_OVERRIDE_BADGE = " (overrides builtin)"


def _format_builtin_entry(primary: str, entry: tuple, width: int) -> str:
    """Format a single builtin command entry."""
    desc = entry[2]
    subcmds = entry[3]
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
    """Format the built-in commands section."""
    lines: list[str] = ["Built-in Commands:"]
    for primary in sorted(all_info.keys()):
        if py_names and primary in py_names:
            continue
        lines.append(_format_builtin_entry(primary, all_info[primary], width))
    lines.append("")
    lines.append("  Tip: /cmd help or /cmd -h shows usage for commands with subcommands.")
    lines.append("")
    return lines
