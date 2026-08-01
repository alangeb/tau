#!/usr/bin/env python3
"""Find unprocessed sessions in $HOME/.local/tau/log/."""
import argparse
import json
import os
import re
import sys

LOG_DIR = os.path.expanduser("~/.local/tau/log")

def find_session_groups():
    """Find all session groups (files sharing PID_TIMESTAMP)."""
    if not os.path.exists(LOG_DIR):
        return {}

    groups = {}
    # Pattern: PID_TIMESTAMP_SEQ.extension
    pattern = re.compile(r"^(\d+_\d{14})")

    for f in os.listdir(LOG_DIR):
        match = pattern.match(f)
        if match:
            group_id = match.group(1)
            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(f)

    return groups

def main():
    parser = argparse.ArgumentParser(description="Find unprocessed sessions")
    parser.add_argument("--log-dir", default=LOG_DIR)
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    log_dir = args.log_dir
    if not os.path.exists(log_dir):
        print(f"ERROR: {log_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    groups = find_session_groups()

    if args.json:
        result = {
            "log_dir": log_dir,
            "groups": groups,
            "count": len(groups),
            "total_files": sum(len(files) for files in groups.values())
        }
        print(json.dumps(result, indent=2))
    else:
        if groups:
            total_files = sum(len(files) for files in groups.values())
            print(f"Found {len(groups)} session groups ({total_files} files) in {log_dir}:")
            for group_id, files in sorted(groups.items())[:20]:  # Show first 20
                print(f"  {group_id}: {len(files)} files")
            if len(groups) > 20:
                print(f"  ... and {len(groups) - 20} more groups")
            sys.exit(1)  # Exit 1 = unprocessed sessions found
        else:
            print("No unprocessed sessions found.")
            sys.exit(0)

if __name__ == "__main__":
    main()
