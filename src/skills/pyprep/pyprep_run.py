#!/usr/bin/env python3
"""Pyprep run helper — run full pyprep sequence."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Tau script path
TAU_SCRIPT = Path(__file__).resolve().parents[2] / "tau.py"


def cmd_run(args):
    """Run full pyprep sequence."""
    target = args.target if hasattr(args, 'target') and args.target else "."
    compact = args.compact if hasattr(args, 'compact') and args.compact else False
    scan_only = args.scan_only if hasattr(args, 'scan_only') and args.scan_only else False

    print(f"# Pyprep — Python Project Preparation")
    print(f"Target: {target}")
    print(f"Compact: {compact}")
    print()

    # Step 1: info
    print("=" * 50)
    print("STEP 1: info")
    print("=" * 50)
    _run_tau_command(["info"], target)
    print()

    # Step 2: pyscan
    print("=" * 50)
    print("STEP 2: pyscan")
    print("=" * 50)
    compact_flag = "compact=True" if compact else "compact=False"
    _run_tau_command([f'pyscan({compact_flag}, path="{target}")'], target)
    print()

    if scan_only:
        print("Scan-only mode — skipping pygraph, pyanalyze, pycheck")
        return

    # Step 3: pygraph
    print("=" * 50)
    print("STEP 3: pygraph")
    print("=" * 50)
    _run_tau_command([f'pygraph(path="{target}", query_type="summary")'], target)
    print()

    # Step 4: pyanalyze
    print("=" * 50)
    print("STEP 4: pyanalyze")
    print("=" * 50)
    _run_tau_command([f'pyanalyze(path="{target}")'], target)
    print()

    # Step 5: pycheck
    print("=" * 50)
    print("STEP 5: pycheck")
    print("=" * 50)
    _run_tau_command([f'pycheck(path="{target}")'], target)
    print()

    print("# Pyprep Complete")
    print("Review results above. Use findings to understand codebase before making changes.")


def cmd_scan(args):
    """Run pyscan only."""
    target = args.target if hasattr(args, 'target') and args.target else "."
    compact = args.compact if hasattr(args, 'compact') and args.compact else False

    print(f"# Pyscan — {target}")
    print()
    compact_flag = "compact=True" if compact else "compact=False"
    _run_tau_command([f'pyscan({compact_flag}, path="{target}")'], target)


def cmd_graph(args):
    """Run pygraph only."""
    target = args.target if hasattr(args, 'target') and args.target else "."
    query = args.query if hasattr(args, 'query') and args.query else "summary"

    print(f"# Pygraph — {target} ({query})")
    print()
    _run_tau_command([f'pygraph(path="{target}", query_type="{query}")'], target)


def cmd_analyze(args):
    """Run pyanalyze only."""
    target = args.target if hasattr(args, 'target') and args.target else "."

    print(f"# Pyanalyze — {target}")
    print()
    _run_tau_command([f'pyanalyze(path="{target}")'], target)


def cmd_check(args):
    """Run pycheck only."""
    target = args.target if hasattr(args, 'target') and args.target else "."

    print(f"# Pycheck — {target}")
    print()
    _run_tau_command([f'pycheck(path="{target}")'], target)


def _run_tau_command(command_parts: list, target: str) -> None:
    """Run a tau.py command and print output."""
    if not TAU_SCRIPT.exists():
        print(f"  ⚠ tau.py not found at {TAU_SCRIPT}")
        print(f"  Run: {TAU_SCRIPT} '{command_parts[0]}'")
        return

    cmd = [sys.executable, str(TAU_SCRIPT)] + command_parts
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(target) if os.path.isabs(target) else os.getcwd()
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    except subprocess.TimeoutExpired:
        print(f"  ⚠ Command timed out: {' '.join(command_parts)}")
    except FileNotFoundError:
        print(f"  ⚠ tau.py not executable. Run manually: {TAU_SCRIPT} {' '.join(command_parts)}")


def main():
    parser = argparse.ArgumentParser(description="Pyprep run helper")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run full pyprep sequence")
    run_parser.add_argument("target", nargs="?", default=".", help="Target directory")
    run_parser.add_argument("--compact", action="store_true", help="Compact pyscan output")
    run_parser.add_argument("--scan-only", action="store_true", help="Run pyscan only")

    scan_parser = subparsers.add_parser("scan", help="Run pyscan only")
    scan_parser.add_argument("target", nargs="?", default=".", help="Target directory")
    scan_parser.add_argument("--compact", action="store_true", help="Compact output")

    graph_parser = subparsers.add_parser("graph", help="Run pygraph only")
    graph_parser.add_argument("target", nargs="?", default=".", help="Target directory")
    graph_parser.add_argument("--query", default="summary", help="Query type")

    analyze_parser = subparsers.add_parser("analyze", help="Run pyanalyze only")
    analyze_parser.add_argument("target", nargs="?", default=".", help="Target directory")

    check_parser = subparsers.add_parser("check", help="Run pycheck only")
    check_parser.add_argument("target", nargs="?", default=".", help="Target directory")

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "graph":
        cmd_graph(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "check":
        cmd_check(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
