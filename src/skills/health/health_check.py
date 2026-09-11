#!/usr/bin/env python3
"""Health check helper — query health endpoints, format output."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Try to import health monitor from agent_core
try:
    from agent_model_health import get_health_monitor, CircuitState, HealthStatus
    HAS_HEALTH = True
except ImportError:
    HAS_HEALTH = False

# Status icons
STATUS_ICONS = {
    "CLOSED": "\u2705",
    "OPEN": "\u274c",
    "HALF_OPEN": "\u26a0",
}


def cmd_status(args):
    """Show health dashboard."""
    if not HAS_HEALTH:
        print("Health monitor not available (agent_model_health not installed)")
        print("Running in standalone mode — showing mock dashboard")
        _print_mock_dashboard()
        return

    monitor = get_health_monitor()
    status = monitor.get_status()
    _print_dashboard(status)


def cmd_check(args):
    """Run connection check."""
    if not HAS_HEALTH:
        print("Health monitor not available")
        print("To check: test API endpoint manually or install agent_model_health")
        return

    monitor = get_health_monitor()
    print("Checking model server connection...")
    result = monitor.check_connection()
    if result:
        print("\u2705 Server is reachable")
    else:
        print("\u274c Server is unreachable")


def cmd_metrics(args):
    """Show raw metrics as JSON."""
    if not HAS_HEALTH:
        print(json.dumps({"error": "Health monitor not available"}, indent=2))
        return

    monitor = get_health_monitor()
    status = monitor.get_status()
    metrics = {
        "circuit_state": status.circuit_state.value,
        "total_successes": status.total_successes,
        "total_failures": status.total_failures,
        "consecutive_failures": status.consecutive_failures,
        "consecutive_successes": status.consecutive_successes,
        "recovery_attempts": status.recovery_attempts,
        "last_error": status.last_error,
    }
    total = status.total_failures + status.total_successes
    metrics["failure_rate"] = round(status.total_failures / total, 4) if total > 0 else 0.0
    print(json.dumps(metrics, indent=2))


def _print_dashboard(status: HealthStatus) -> None:
    """Print formatted health dashboard."""
    print("=" * 50)
    print("  MODEL SERVER HEALTH DASHBOARD")
    print("=" * 50)
    print()

    icon = STATUS_ICONS.get(status.circuit_state.value, "?")
    state_label = status.circuit_state.value.upper()
    prefix = "\u2705" if status.circuit_state == CircuitState.CLOSED else "\u274c" if status.circuit_state == CircuitState.OPEN else "\u26a0"
    print(f"  Circuit: {prefix} {icon} {state_label}")

    total = status.total_failures + status.total_successes
    rate = status.total_failures / total if total > 0 else 0.0

    print(f"  Total successes:      {status.total_successes}")
    print(f"  Total failures:       {status.total_failures}")
    print(f"  Consecutive failures: {status.consecutive_failures}")
    print(f"  Consecutive successes:{status.consecutive_successes}")
    print(f"  Failure rate:         {rate:.1%}")
    print(f"  Recovery attempts:    {status.recovery_attempts}")
    if status.last_error:
        print(f"  Last error:           {status.last_error}")
    print()


def _print_mock_dashboard():
    """Print mock dashboard for standalone use."""
    print("=" * 50)
    print("  MODEL SERVER HEALTH DASHBOARD (STANDALONE)")
    print("=" * 50)
    print()
    print("  Circuit: ? UNKNOWN")
    print("  Status:  Health monitor not loaded")
    print()
    print("  To use health monitoring:")
    print("    1. Run within tau.py agent context")
    print("    2. Or install agent_model_health package")
    print()


def main():
    parser = argparse.ArgumentParser(description="Health check helper")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Show health dashboard")
    subparsers.add_parser("check", help="Run connection check")
    subparsers.add_parser("metrics", help="Show raw metrics (JSON)")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "metrics":
        cmd_metrics(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
