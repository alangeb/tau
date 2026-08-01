#!/usr/bin/env python3
"""Performance profiling helper — profile functions, commands, and analyze audit logs."""
from __future__ import annotations

import cProfile
import io
import pstats
import re
import subprocess
import sys
import time
from pathlib import Path


def profile_function(func, *args, **kwargs) -> str:
    """Profile a function and return formatted results."""
    pr = cProfile.Profile()
    pr.enable()
    func(*args, **kwargs)
    pr.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)
    return s.getvalue()


def time_execution(func, *args, **kwargs) -> tuple:
    """Time function execution and return (result, duration_seconds)."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    duration = time.perf_counter() - start
    return result, duration


def profile_command(command: str, timeout: int = 60) -> dict:
    """Profile a shell command and return timing stats.
    
    Returns dict with command, returncode, duration_s, stdout_len, stderr_len.
    """
    start = time.perf_counter()
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=timeout
    )
    duration = time.perf_counter() - start
    
    return {
        "command": command,
        "returncode": result.returncode,
        "duration_s": round(duration, 3),
        "stdout_len": len(result.stdout),
        "stderr_len": len(result.stderr),
        "stdout_preview": result.stdout[:200] if result.stdout else "",
        "stderr_preview": result.stderr[:200] if result.stderr else "",
    }


def analyze_audit_durations(audit_file: str) -> dict:
    """Analyze tool call durations from a tau audit log file.
    
    Returns dict with total_calls, avg_duration_ms, max_duration_ms, 
    slowest_calls (top 10), and duration_distribution.
    """
    path = Path(audit_file)
    if not path.exists():
        return {"error": f"File not found: {audit_file}"}
    
    durations = []
    tool_durations: dict[str, list[float]] = {}
    slowest: list[dict] = []
    
    content = path.read_text()
    
    # Match duration_ms=XXXX patterns
    for m in re.finditer(r"final_name='(\w+)'.*?duration_ms=(\d+)", content, re.DOTALL):
        tool_name = m.group(1)
        duration = int(m.group(2))
        durations.append(duration)
        
        if tool_name not in tool_durations:
            tool_durations[tool_name] = []
        tool_durations[tool_name].append(duration)
        
        slowest.append({"tool": tool_name, "duration_ms": duration})
    
    # Sort by duration descending
    slowest.sort(key=lambda x: x["duration_ms"], reverse=True)
    
    # Calculate per-tool stats
    tool_stats = {}
    for tool, durs in tool_durations.items():
        tool_stats[tool] = {
            "count": len(durs),
            "avg_ms": round(sum(durs) / len(durs), 1),
            "max_ms": max(durs),
            "total_ms": sum(durs),
        }
    
    return {
        "audit_file": str(path),
        "total_calls": len(durations),
        "avg_duration_ms": round(sum(durations) / len(durations), 1) if durations else 0,
        "max_duration_ms": max(durations) if durations else 0,
        "min_duration_ms": min(durations) if durations else 0,
        "total_time_s": round(sum(durations) / 1000, 2),
        "tool_stats": dict(sorted(tool_stats.items(), key=lambda x: x[1]["total_ms"], reverse=True)[:10]),
        "slowest_calls": slowest[:10],
    }


def benchmark_tool_calls(commands: list[str]) -> list[dict]:
    """Run multiple commands and compare execution times.
    
    Args:
        commands: List of shell commands to benchmark
        
    Returns:
        List of result dicts sorted by duration
    """
    results = [profile_command(cmd) for cmd in commands]
    results.sort(key=lambda x: x["duration_s"])
    return results


def main() -> None:
    if len(sys.argv) < 2:
        print("Performance profiling helper")
        print(f"Usage: {sys.argv[0]} {{profile|time|audit|benchmark}} [args...]")
        return
    
    cmd = sys.argv[1]
    if cmd == "profile":
        # Profile a command
        target = sys.argv[2] if len(sys.argv) > 2 else "echo hello"
        print(profile_command(target))
    elif cmd == "time":
        target = sys.argv[2] if len(sys.argv) > 2 else "echo hello"
        result = profile_command(target)
        print(f"{result['duration_s']}s | rc={result['returncode']}")
    elif cmd == "audit":
        audit_file = sys.argv[2] if len(sys.argv) > 2 else ""
        import json
        print(json.dumps(analyze_audit_durations(audit_file), indent=2))
    elif cmd == "benchmark":
        commands = sys.argv[2:] if len(sys.argv) > 2 else ["echo test", "date"]
        import json
        print(json.dumps(benchmark_tool_calls(commands), indent=2))
    else:
        print(f"Unknown: {cmd}. Use: profile, time, audit, benchmark")
        sys.exit(1)


if __name__ == "__main__":
    main()
