#!/usr/bin/env python3
"""Orchestrate manifest helper — list, show, verify manifests."""
import argparse
import glob
import json
import os
import sys
from pathlib import Path

MANIFESTS_DIR = Path(os.environ.get("TAU_DIR", os.path.expanduser("~/.local/tau"))) / "manifests"
# Fallback to src-relative
if not MANIFESTS_DIR.exists():
    MANIFESTS_DIR = Path(__file__).resolve().parents[2] / ".tau" / "manifests"


def find_manifests():
    """Find all manifest files."""
    if not MANIFESTS_DIR.exists():
        return []
    manifests = sorted(MANIFESTS_DIR.glob("manifest-*.md"), reverse=True)
    return manifests


def parse_manifest(path):
    """Parse manifest frontmatter."""
    with open(path) as f:
        content = f.read()
    if not content.startswith("---"):
        return {}
    frontmatter = content.split("---")[1]
    result = {}
    for line in frontmatter.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            result[key.strip()] = val.strip()
    return result


def load_state(path):
    """Load state.json for a manifest."""
    state_path = str(path).replace(".md", ".state.json")
    if os.path.exists(state_path):
        with open(state_path) as f:
            return json.load(f)
    return {}


def cmd_list(args):
    """List manifests with status."""
    manifests = find_manifests()
    if not manifests:
        print("No manifests found.")
        return
    print(f"{'Name':<30} {'Goal':<40} {'Status':<12} {'Subtasks':<10}")
    print("-" * 92)
    for m in manifests:
        meta = parse_manifest(m)
        state = load_state(m)
        goal = meta.get("goal", meta.get("title", "?"))[:38]
        status = meta.get("status", "unknown")
        subtasks = meta.get("subtasks", "?")
        if isinstance(subtasks, str):
            subtasks = str(subtasks.count("\n") + 1)
        print(f"{m.name:<30} {goal:<40} {status:<12} {subtasks:<10}")


def cmd_show(args):
    """Show manifest details."""
    manifests = find_manifests()
    if not manifests:
        print("No manifests found.")
        return
    target = args.name or manifests[0].name
    path = MANIFESTS_DIR / target
    if not path.exists():
        print(f"Manifest not found: {target}")
        return
    with open(path) as f:
        print(f.read())
    state = load_state(path)
    if state:
        print("\n--- State ---")
        print(json.dumps(state, indent=2))


def cmd_verify(args):
    """Check manifest verification status."""
    manifests = find_manifests()
    for m in manifests:
        meta = parse_manifest(m)
        state = load_state(m)
        status = meta.get("status", "unknown")
        retries = state.get("retries", 0)
        print(f"{m.name}: status={status} retries={retries}")


def main():
    parser = argparse.ArgumentParser(description="Orchestrate manifest helper")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list", help="List manifests")
    show_p = sub.add_parser("show", help="Show manifest")
    show_p.add_argument("name", nargs="?", help="Manifest name")
    sub.add_parser("verify", help="Check verification status")
    args = parser.parse_args()
    if args.command == "list" or not args.command:
        cmd_list(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "verify":
        cmd_verify(args)


if __name__ == "__main__":
    main()
