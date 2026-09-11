"""Status display functions for TauErgon console.

Handles agent status, exit summaries, context status, and cache hit rates.
"""
from __future__ import annotations

import datetime
import os
from pathlib import Path

from agent_console.primitives import (
    _cw,
    blank_line,
    compute_duration,
    display_info,
    display_success,
)

__all__ = [
    "agent_status",
    "exit_summary",
    "print_agent_exit_summary",
    "print_context_status",
    "build_cache_hit_rates_str",
]


# ── Status Display ────────────────────────────────────────────────────────────


def agent_status(status: object) -> None:
    """Display comprehensive agent status information."""
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
