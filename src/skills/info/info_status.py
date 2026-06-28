#!/usr/bin/env python3
"""info_status.py — Quick agent status check."""
import os, re, glob
from pathlib import Path

def check_context_usage(log_dir="~/.local/tau/log"):
    """Check context usage from recent audit logs."""
    log_dir = os.path.expanduser(log_dir)
    logs = sorted(glob.glob(os.path.join(log_dir, "*_2026*_1.audit")), reverse=True)[:5]
    for log in logs:
        with open(log) as f:
            for line in f:
                if "context_usage" in line.lower() or "token" in line.lower():
                    print(f"{os.path.basename(log)}: {line.strip()}")
                    break

def check_active_sessions():
    """Check active tmux agent sessions."""
    import subprocess
    result = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name}"],
        capture_output=True, text=True
    )
    sessions = [s for s in result.stdout.strip().split('\n') if 'tmux-agent-' in s]
    if sessions:
        print(f"Active sessions: {len(sessions)}")
        for s in sessions:
            print(f"  - {s}")
    else:
        print("No active agent sessions")

if __name__ == "__main__":
    check_active_sessions()
    print()
    check_context_usage()
