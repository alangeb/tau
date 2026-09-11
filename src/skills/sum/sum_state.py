#!/usr/bin/env python3
"""Sum state helper — collect state info, generate summary template."""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def cmd_generate(args):
    """Generate a state summary with collected data."""
    print("Collecting state information...")
    print()

    # Git status
    git_changes = _get_git_status()

    # Recent git log
    git_log = _get_git_log()

    # File tree (top level)
    file_tree = _get_file_tree()

    # Generate summary
    print("# EXECUTION STATE SUMMARY")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    print("### 1. EXECUTION SUMMARY")
    print("* **Objective:** [FILL IN]")
    print("* **Status:** [COMPLETED / IN-PROGRESS / BLOCKED / FAILED]")
    print("* **Scope of Changes:** [FILL IN]")
    print()

    print("### 2. ACTIONS TAKEN & OUTCOMES")
    print("#### What Was Attempted & Worked")
    print("* **[Action 1]:** [What you did] -> **[Result]:** [Why it succeeded]")
    print()
    print("#### What Was Attempted & Failed")
    print("* **[Attempt 1]:** [What you tried] -> **[Failure Reason]:** [Error or blocker]")
    print()

    print("### 3. KNOWLEDGE ACQUIRED & DECISIONS MADE")
    print("* **Technical Insights:** [FILL IN]")
    print("* **Architectural Decisions:** [FILL IN]")
    print("* **Environmental/State Changes:** [FILL IN]")
    print()

    print("### 4. THE TODO BACKLOG (LEFTOVER WORK)")
    print("* **[ ] [High Priority]** [Immediate next step]")
    print("* **[ ] [Medium Priority]** [Refactoring, tests]")
    print("* **[ ] [Low Priority]** [Docs, cleanup]")
    print()

    print("### 5. PROPOSED NEXT STEPS (STRATEGY)")
    print("1. **[Step 1]:** [First action for next agent]")
    print("2. **[Step 2]:** [Validation steps]")
    print()

    # Append collected data
    print("---")
    print("## COLLECTED DATA")
    print()

    if git_changes:
        print("### Git Status")
        print("```")
        print(git_changes)
        print("```")
        print()

    if git_log:
        print("### Recent Commits")
        print("```")
        print(git_log)
        print("```")
        print()

    if file_tree:
        print("### File Tree (Top Level)")
        print("```")
        print(file_tree)
        print("```")
        print()


def cmd_template(args):
    """Print empty summary template."""
    print("# EXECUTION STATE SUMMARY")
    print()
    print("### 1. EXECUTION SUMMARY")
    print("* **Objective:** [FILL IN]")
    print("* **Status:** [COMPLETED / IN-PROGRESS / BLOCKED / FAILED]")
    print("* **Scope of Changes:** [FILL IN]")
    print()
    print("### 2. ACTIONS TAKEN & OUTCOMES")
    print("#### What Was Attempted & Worked")
    print("* **[Action 1]:** [What you did] -> **[Result]:** [Why it succeeded]")
    print()
    print("#### What Was Attempted & Failed")
    print("* **[Attempt 1]:** [What you tried] -> **[Failure Reason]:** [Error or blocker]")
    print()
    print("### 3. KNOWLEDGE ACQUIRED & DECISIONS MADE")
    print("* **Technical Insights:** [FILL IN]")
    print("* **Architectural Decisions:** [FILL IN]")
    print("* **Environmental/State Changes:** [FILL IN]")
    print()
    print("### 4. THE TODO BACKLOG (LEFTOVER WORK)")
    print("* **[ ] [High Priority]** [Immediate next step]")
    print("* **[ ] [Medium Priority]** [Refactoring, tests]")
    print("* **[ ] [Low Priority]** [Docs, cleanup]")
    print()
    print("### 5. PROPOSED NEXT STEPS (STRATEGY)")
    print("1. **[Step 1]:** [First action for next agent]")
    print("2. **[Step 2]:** [Validation steps]")


def cmd_git_status(args):
    """Print git status only."""
    status = _get_git_status()
    if status:
        print(status)
    else:
        print("No git repository found")


def _get_git_status() -> str:
    """Get git status output."""
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def _get_git_log(count: int = 5) -> str:
    """Get recent git log."""
    try:
        result = subprocess.run(
            ["git", "log", f"--oneline", f"-{count}", "--graph"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def _get_file_tree(max_depth: int = 2) -> str:
    """Get file tree."""
    try:
        result = subprocess.run(
            ["tree", f"--maxdepth", str(max_depth), "-L", str(max_depth)],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()[:2000] if result.returncode == 0 else ""
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def main():
    parser = argparse.ArgumentParser(description="Sum state helper")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("generate", help="Generate full state summary")
    subparsers.add_parser("template", help="Print empty template")
    subparsers.add_parser("git-status", help="Show git status only")

    args = parser.parse_args()

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "template":
        cmd_template(args)
    elif args.command == "git-status":
        cmd_git_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
