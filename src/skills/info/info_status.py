#!/usr/bin/env python3
"""info_status.py — Agent status reporter: sessions, context, system info."""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
from pathlib import Path


def check_active_sessions() -> list[dict]:
    """Check active tmux agent sessions and return structured info."""
    try:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}:#{session_attached}"],
            capture_output=True, text=True, timeout=5
        )
        sessions = []
        for line in result.stdout.strip().split("\n"):
            if "tmux-agent-" in line:
                name, attached = line.rsplit(":", 1)
                sessions.append({
                    "name": name,
                    "attached": int(attached) == 1,
                })
        return sessions
    except Exception as e:
        return [{"error": str(e)}]


def get_session_output(session_name: str, lines: int = 10) -> str:
    """Get recent output from a tmux session."""
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", session_name, "-p", "-S", f"-{lines}"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout
    except Exception:
        return f"Error: Could not capture session '{session_name}'"


def check_context_usage(log_dir: str = "~/.local/tau/log") -> list[dict]:
    """Check context usage from recent audit logs."""
    log_dir = os.path.expanduser(log_dir)
    results = []
    logs = sorted(glob.glob(os.path.join(log_dir, "*.audit")), reverse=True)[:5]
    for log in logs:
        try:
            with open(log) as f:
                for line in f:
                    if "token" in line.lower() and ("usage" in line.lower() or "/" in line):
                        results.append({
                            "file": os.path.basename(log),
                            "line": line.strip(),
                        })
                        break
        except (OSError, PermissionError):
            continue
    return results


def get_system_info() -> dict:
    """Get basic system information."""
    info: dict = {
        "cwd": os.getcwd(),
        "pid": os.getpid(),
        "user": os.environ.get("USER", "unknown"),
    }
    
    # Disk usage for home directory
    try:
        stat = os.statvfs(Path.home())
        total_gb = (stat.f_frsize * stat.f_blocks) / (1024**3)
        free_gb = (stat.f_frsize * stat.f_bavail) / (1024**3)
        info["disk"] = {"total_gb": round(total_gb, 1), "free_gb": round(free_gb, 1)}
    except Exception:
        pass
    
    # Memory info (Linux)
    try:
        with open("/proc/meminfo") as f:
            mem = f.read(500)
        import re
        total_m = re.search(r"MemTotal:\s+(\d+)", mem)
        avail_m = re.search(r"MemAvailable:\s+(\d+)", mem)
        if total_m and avail_m:
            info["memory"] = {
                "total_mb": int(total_m.group(1)) // 1024,
                "available_mb": int(avail_m.group(1)) // 1024,
            }
    except Exception:
        pass
    
    return info


def full_status() -> dict:
    """Generate full status report."""
    return {
        "system": get_system_info(),
        "tmux_sessions": check_active_sessions(),
        "recent_context_logs": check_context_usage(),
    }


def print_status() -> None:
    """Print formatted status report."""
    status = full_status()
    
    print("=== System ===")
    sys_info = status["system"]
    print(f"  CWD: {sys_info.get('cwd', '?')}")
    print(f"  PID: {sys_info.get('pid', '?')}")
    if "disk" in sys_info:
        print(f"  Disk: {sys_info['disk']['free_gb']}GB / {sys_info['disk']['total_gb']}GB free")
    if "memory" in sys_info:
        print(f"  Memory: {sys_info['memory']['available_mb']}MB / {sys_info['memory']['total_mb']}MB available")
    
    print(f"\n=== Tmux Sessions ({len(status['tmux_sessions'])}) ===")
    for s in status["tmux_sessions"][:10]:
        if "error" in s:
            print(f"  Error: {s['error']}")
        else:
            state = "attached" if s["attached"] else "detached"
            print(f"  {s['name']} [{state}]")
    
    print(f"\n=== Recent Context Logs ({len(status['recent_context_logs'])}) ===")
    for log in status["recent_context_logs"][:5]:
        print(f"  {log['file']}: {log['line'][:80]}")


def main() -> None:
    if len(sys.argv) < 2:
        print_status()
        return
    
    cmd = sys.argv[1]
    if cmd == "sessions":
        print(json.dumps(check_active_sessions(), indent=2))
    elif cmd == "output":
        session = sys.argv[2] if len(sys.argv) > 2 else ""
        lines = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        print(get_session_output(session, lines))
    elif cmd == "context":
        print(json.dumps(check_context_usage(), indent=2))
    elif cmd == "system":
        print(json.dumps(get_system_info(), indent=2))
    elif cmd == "full":
        print(json.dumps(full_status(), indent=2, default=str))
    elif cmd == "status":
        print_status()
    else:
        print(f"Usage: {sys.argv[0]} {{sessions|output|context|system|full|status}} [args]")
        sys.exit(1)


if __name__ == "__main__":
    main()
