"""Miscellaneous display functions for TauErgon console.

Split from the original monolithic display.py. Contains simple one-line
messages, usage displays, loop warnings, LLM timeout messages, validation
retries, and compression step summaries.
"""
from __future__ import annotations

import sys

from agent_console.primitives import (
    _cw,
    blank_line,
    display_error,
    display_info,
    display_warning,
)
from agent_models import Colors

__all__ = [
    # Simple display
    "error_display",
    "undo_message",
    "restart_flow",
    "subagent_usage",
    "fork_usage",
    "subagent_output_header",
    "loop_warning",
    # LLM display
    "llm_timeout_message",
    "llm_validation_retry",
    "compression_step_summary",
]


# ── Simple Display ────────────────────────────────────────────────────────────


def error_display(label: str, detail: str) -> None:
    display_error(f"[{label}]")
    sys.stdout.write(f"{detail}\n")


def undo_message(removed: int) -> None:
    if removed == 0:
        display_warning("Undid 0 message(s). Nothing to undo.")
    else:
        display_info(f"Undid {removed} message(s). Context now ends before last user input.")


def restart_flow(command_args: str) -> None:
    from agent_console.templates import restart_flow_info, restart_flow_success
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
    if not 1 <= level <= 4:
        raise ValueError(
            f"loop_warning: level must be 1-4, got {level}"
        )
    _cw(Colors.YELLOW if level == 1 else Colors.RED,
        ("", "\u26a0\ufe0f  ", "\U0001f534 ", "\U0001f6a8 ", "\U0001f4a5 ")[level] + message)


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
    arrow = f"{bytes_before:,} \u2192 {bytes_after:,} bytes, {msgs_before} \u2192 {msgs_after} msgs"
    status_tag = f" [{status}]" if status else ""
    _cw(
        Colors.BLUE,
        f"[COMPRESS] STEP {step_idx}/{total_steps} {step_name}: {arrow} | {action_summary}{status_tag}",
    )
