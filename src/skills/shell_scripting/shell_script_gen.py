#!/usr/bin/env python3
"""shell_script_gen.py — Generate common shell script patterns.
Usage: python3 skills/shell_scripting/shell_script_gen.py <pattern> [args...]

Patterns:
  audit_count    — Count tool calls in audit logs
  audit_skill    — Count skill loads in audit logs
  audit_errors   — Count errors in audit logs
  parse_json     — Parse JSON from file/stream
  batch_rename   — Batch rename files
  find_replace   — Find and replace across files
  log_tail       — Tail multiple log files
"""
import sys
import re
import os
import json
from pathlib import Path

LOG_DIR = Path.home() / ".local" / "tau" / "log"


def audit_count(pattern=None):
    """Count tool calls in audit logs."""
    files = sorted(LOG_DIR.glob("*_1.audit"), key=os.path.getmtime, reverse=True)[:20]
    counts = {}
    for f in files:
        for line in f.read_text().split("\n"):
            if "final_name='" in line:
                m = re.search(r"final_name='([^']*)'", line)
                if m:
                    name = m.group(1)
                    if pattern and pattern not in name:
                        continue
                    counts[name] = counts.get(name, 0) + 1
    for name, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"{count:6d} {name}")


def audit_skill():
    """Count skill loads in audit logs."""
    files = sorted(LOG_DIR.glob("*_1.audit"), key=os.path.getmtime, reverse=True)[:20]
    counts = {}
    for f in files:
        for line in f.read_text().split("\n"):
            if '"skill_name"' in line:
                m = re.search(r'"skill_name":\s*"([^"]*)"', line)
                if m:
                    name = m.group(1)
                    counts[name] = counts.get(name, 0) + 1
    for name, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"{count:6d} {name}")


def audit_errors():
    """Count errors in audit logs."""
    files = sorted(LOG_DIR.glob("*_1.audit"), key=os.path.getmtime, reverse=True)[:20]
    total = 0
    for f in files:
        text = f.read_text()
        total += text.count("TOOL_ERROR") + text.count("TOOL_BLOCKED")
    print(f"Total errors in last 20 sessions: {total}")


def parse_json(input_path=None):
    """Parse JSON from file or stdin."""
    if input_path:
        data = json.loads(Path(input_path).read_text())
    else:
        data = json.loads(sys.stdin.read())
    print(json.dumps(data, indent=2))


def batch_rename(directory, pattern, replacement):
    """Batch rename files matching pattern."""
    dir_path = Path(directory)
    for f in dir_path.glob(pattern):
        new_name = re.sub(pattern, replacement, f.name)
        new_path = f.parent / new_name
        print(f"WOULD: {f} -> {new_path}")


def find_replace(directory, search, replace, pattern="*"):
    """Find and replace across files."""
    dir_path = Path(directory)
    for f in dir_path.glob(pattern):
        if not f.is_file():
            continue
        content = f.read_text()
        if search in content:
            new_content = content.replace(search, replace)
            print(f"WOULD REPLACE in {f}: {content.count(search)} occurrences")


def log_tail(files, lines=30):
    """Tail multiple log files."""
    for f in files:
        print(f"\n=== {f} ===")
        Path(f).read_text().split("\n")[-lines:]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "audit_count":
        audit_count(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "audit_skill":
        audit_skill()
    elif cmd == "audit_errors":
        audit_errors()
    elif cmd == "parse_json":
        parse_json(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "batch_rename":
        batch_rename(*sys.argv[2:5])
    elif cmd == "find_replace":
        find_replace(*sys.argv[2:6])
    elif cmd == "log_tail":
        log_tail(sys.argv[2:], int(sys.argv[3]) if len(sys.argv) > 3 else 30)
    else:
        print(f"Unknown pattern: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
