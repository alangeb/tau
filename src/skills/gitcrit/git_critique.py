#!/usr/bin/env python3
"""Git critique helper — analyze recent commits, generate critique."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# Commit message patterns
MSG_TOO_SHORT = 10
MSG_SUBJECT_MAX = 50
MSG_BODY_RECOMMENDED = 20

# Valid commit types
VALID_TYPES = {"feat", "fix", "refactor", "docs", "style", "test", "chore", "perf", "ci", "revert"}

# Bad message patterns
BAD_PATTERNS = [
    (re.compile(r"^(fix|update|wip|change|modify)$", re.I), "Too vague — describe what was changed"),
    (re.compile(r"^wip\b", re.I), "WIP commits should not be in history"),
    (re.compile(r"^[a-z]", re.I), "Subject should start with capital letter"),
    (re.compile(r"\.$"), "Subject should not end with period"),
]


def cmd_analyze(args):
    """Analyze recent commits."""
    count = args.count if hasattr(args, 'count') and args.count else 10
    commits = _get_commits(count)

    if not commits:
        print("No commits found")
        return

    print(f"# Git Critique — Last {count} Commits")
    print()

    for commit in commits:
        _critique_commit(commit)
        print()


def cmd_messages(args):
    """Check commit message quality."""
    count = args.count if hasattr(args, 'count') and args.count else 10
    commits = _get_commits(count)

    if not commits:
        print("No commits found")
        return

    print("# Commit Message Quality Check")
    print()

    issues_found = 0
    for commit in commits:
        issues = _check_message(commit)
        if issues:
            print(f"### {commit['hash']} — {len(issues)} issue(s)")
            for issue in issues:
                print(f"  ⚠ {issue}")
            print()
            issues_found += 1

    if issues_found == 0:
        print("✅ All commit messages look good")
    else:
        print(f"Found {issues_found} commit(s) with message issues")


def cmd_scope(args):
    """Check change scope."""
    count = args.count if hasattr(args, 'count') and args.count else 5
    commits = _get_commits(count)

    if not commits:
        print("No commits found")
        return

    print("# Change Scope Analysis")
    print()

    for commit in commits:
        stats = _get_diff_stats(commit["hash"])
        if stats:
            files_changed = stats.get("files", 0)
            insertions = stats.get("insertions", 0)
            deletions = stats.get("deletions", 0)

            scope = "small" if files_changed <= 3 else "medium" if files_changed <= 10 else "large"
            scope_icon = {"small": "🟢", "medium": "🟡", "large": "🔴"}.get(scope, "⚪")

            print(f"{scope_icon} {commit['hash']} — {scope} ({files_changed} files, +{insertions}/-{deletions})")
            print(f"    {commit['subject']}")

            if files_changed > 10:
                print(f"    ⚠ Consider splitting into smaller commits")
            print()


def _get_commits(count: int = 10) -> list:
    """Get recent commits."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{count}", "--format=%H|%s|%b"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 2)
            commit = {
                "hash": parts[0][:8] if len(parts) > 0 else "",
                "subject": parts[1] if len(parts) > 1 else "",
                "body": parts[2] if len(parts) > 2 else "",
            }
            commits.append(commit)
        return commits
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def _check_message(commit: dict) -> list:
    """Check commit message for issues."""
    issues = []
    subject = commit["subject"]
    body = commit["body"]

    if not subject:
        issues.append("Empty subject line")
        return issues

    if len(subject) < MSG_TOO_SHORT:
        issues.append(f"Subject too short ({len(subject)} chars, min {MSG_TOO_SHORT})")

    if len(subject) > MSG_SUBJECT_MAX:
        issues.append(f"Subject too long ({len(subject)} chars, max {MSG_SUBJECT_MAX})")

    # Check for conventional commit format
    if not re.match(r"^(feat|fix|refactor|docs|style|test|chore|perf|ci|revert):", subject, re.I):
        issues.append("Not conventional commit format (type: description)")

    # Check bad patterns
    for pattern, msg in BAD_PATTERNS:
        if pattern.match(subject):
            issues.append(msg)

    # Body check for non-trivial commits
    if len(subject) > 30 and not body.strip():
        issues.append("Complex change without body explanation")

    return issues


def _critique_commit(commit: dict) -> None:
    """Print critique for a single commit."""
    print(f"### {commit['hash']}")
    print(f"Subject: {commit['subject']}")

    issues = _check_message(commit)
    if issues:
        for issue in issues:
            print(f"  ⚠ {issue}")
    else:
        print("  ✅ Message looks good")

    if commit["body"]:
        print(f"  Body: {commit['body'][:100]}...")

    stats = _get_diff_stats(commit["hash"])
    if stats:
        print(f"  Changes: {stats.get('files', 0)} files, +{stats.get('insertions', 0)}/-{stats.get('deletions', 0)}")


def _get_diff_stats(commit_hash: str) -> dict:
    """Get diff stats for a commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "--numstat", f"{commit_hash}~1", commit_hash],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return {}

        files = 0
        insertions = 0
        deletions = 0
        for line in result.stdout.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) >= 3:
                files += 1
                try:
                    ins = int(parts[0]) if parts[0] != "-" else 0
                    dels = int(parts[1]) if parts[1] != "-" else 0
                    insertions += ins
                    deletions += dels
                except ValueError:
                    pass

        return {"files": files, "insertions": insertions, "deletions": deletions}
    except (subprocess.SubprocessError, FileNotFoundError):
        return {}


def main():
    parser = argparse.ArgumentParser(description="Git critique helper")
    subparsers = parser.add_subparsers(dest="command")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze recent commits")
    analyze_parser.add_argument("--count", type=int, default=10, help="Number of commits")

    messages_parser = subparsers.add_parser("messages", help="Check message quality")
    messages_parser.add_argument("--count", type=int, default=10, help="Number of commits")

    scope_parser = subparsers.add_parser("scope", help="Check change scope")
    scope_parser.add_argument("--count", type=int, default=5, help="Number of commits")

    args = parser.parse_args()

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "messages":
        cmd_messages(args)
    elif args.command == "scope":
        cmd_scope(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
