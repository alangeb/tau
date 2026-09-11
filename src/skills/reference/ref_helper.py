#!/usr/bin/env python3
"""ref_helper.py — Quick reference lookup for Tau commands, configs, and patterns."""
import json
import sys
import os

REFERENCE = {
    "commands": {
        "/fork": "Spawn fork (full memory)",
        "/subagent": "Spawn subagent (blank slate)",
        "/background": "Run background task",
        "/status": "Agent status",
        "/manifests": "List manifests, show hierarchy",
        "/skill": "Load skill",
        "/wiki": "Wiki operations",
    },
    "config": {
        "log_dir": "~/.local/tau/log/",
        "skills_dir": "skills/",
        "tools_dir": "tools/",
        "commands_dir": "commands/",
        "test_dir": "$HOME/tau/test/",
        "src_dir": "$HOME/tau/src/",
    },
    "tools": {
        "bash": "Execute shell commands",
        "file_read": "Read file with line numbers",
        "file_write": "Create/overwrite file",
        "file_edit": "Replace exact text in file",
        "grep": "Search for patterns",
        "pyscan": "Analyze Python project structure",
        "pygraph": "Cross-file call graphs",
        "pyanalyze": "Unused functions/imports",
        "background_run": "Run command in background",
        "fork": "Spawn subagent with full memory",
        "subagent": "Spawn subagent (blank slate)",
        "info": "Agent status and context usage",
        "manifest_create": "Create manifest for goal tracking",
        "manifest_update": "Update manifest sections with auto-verify",
        "manifest_tree": "Show manifest hierarchy",
        "skill": "Load skill content",
        "wiki": "Wiki operations",
    },
}

def lookup(category=None, key=None):
    """Look up reference information."""
    if category and key:
        if category in REFERENCE and key in REFERENCE[category]:
            print(f"{key}: {REFERENCE[category][key]}")
            return
        print(f"Not found: {category}/{key}")
    elif category:
        if category in REFERENCE:
            for k, v in REFERENCE[category].items():
                print(f"  {k}: {v}")
        else:
            print(f"Category not found: {category}")
    else:
        for cat in REFERENCE:
            print(f"\n## {cat}")
            for k, v in REFERENCE[cat].items():
                print(f"  {k}: {v}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        lookup(*sys.argv[1:])
    else:
        lookup()
