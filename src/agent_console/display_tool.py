"""Tool display functions for TauErgon console.

Handles display of tool invocations, results, errors, listings, and agent tables.
"""
from __future__ import annotations

import json
import sys

from agent_console.primitives import (
    display_error,
    display_info,
    display_success,
    format_duration_ms,
)

__all__ = [
    "tool_start",
    "tool_output",
    "tool_error_detail",
    "tools_listing",
    "tools_json_schema",
    "agents_table_header",
    "agents_table_row",
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

    if error is not None:
        error_type = type(error).__name__
        error_msg = str(error)
        display_error(f"Error type: {error_type}")
        if error_msg:
            display_error(f"Error message: {error_msg}")

    if duration_ms is not None:
        display_error(f"Duration: {format_duration_ms(duration_ms)}")

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
