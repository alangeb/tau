"""Low-level console I/O primitives for TauErgon.

All other console modules import from here. This is the foundation layer
with zero dependencies on other agent_console submodules.

Exports:
    - Timing utilities: compute_duration, format_duration_ms
    - Color helpers: _cw, _role_color
    - Output primitives: echo, blank_line, echo_no_newline, prompt, status, reasoning, verbose
"""
from __future__ import annotations

import sys
import time

from agent_models import Colors


__all__ = [
    # Timing
    "compute_duration",
    "format_duration_ms",
    # Color helpers
    "_cw",
    "_role_color",
    # Output primitives
    "echo",
    "blank_line",
    "echo_no_newline",
    "prompt",
    "status",
    "reasoning",
    "verbose",
]


def compute_duration(obj: object, attr: str = "_start_time") -> float:
    """Compute session duration from a start-time attribute on *obj*.

    Returns 0 if *obj* has no such attribute (e.g., start time never set).
    """
    return time.time() - getattr(obj, attr, time.time()) if hasattr(obj, attr) else 0


def format_duration_ms(duration_ms: float) -> str:
    """Format a duration in milliseconds into a human-readable string.

    Uses seconds for values >= 1000ms, milliseconds otherwise.
    """
    if duration_ms >= 1000:
        return f"{duration_ms / 1000:.1f}s"
    return f"{duration_ms:.0f}ms"


# ── Color helpers ────────────────────────────────────────────────────────────


def _cw(color: str, text: str, newline: bool = True) -> None:
    """Write colorized text to stdout."""
    sys.stdout.write(f"{color}{text}{Colors.RESET}" + ("\n" if newline else ""))


def _role_color(role: str) -> str:
    """Return ANSI color code for the specified message role."""
    if role == "user":
        return Colors.RESET
    if role in ("tool", "tool_call"):
        return Colors.CYAN
    return Colors.GREEN


# ── Output primitives ────────────────────────────────────────────────────────


def echo(text: str, newline: bool = True) -> None:
    """Write text to stdout."""
    sys.stdout.write(text + ("\n" if newline else ""))


def blank_line() -> None:
    """Write a blank line to stdout."""
    sys.stdout.write("\n")


def echo_no_newline(text: str) -> None:
    """Write text to stdout without trailing newline."""
    sys.stdout.write(text)


def prompt(text: str = "") -> None:
    """Display a prompt in cyan, flush stdout."""
    _cw(Colors.CYAN, text, newline=False)
    sys.stdout.flush()


def status(text: str) -> None:
    """Display a status message in cyan."""
    _cw(Colors.CYAN, text)


def reasoning(text: str) -> None:
    """Display a reasoning message."""
    _cw(Colors.REASONING, f"[REASON] {text}")


def verbose(text: str) -> None:
    """Display a verbose message in green."""
    _cw(Colors.GREEN, text)
