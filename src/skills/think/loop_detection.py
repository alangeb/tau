#!/usr/bin/env python3
"""loop_detection.py — Detect stuck loops and repeating patterns in audit logs."""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


def extract_tool_calls(audit_file: str) -> list[str]:
    """Extract sequence of tool calls from an audit file."""
    tool_calls = []
    try:
        with open(audit_file) as f:
            for line in f:
                m = re.search(r"final_name='(\w+)'", line)
                if m:
                    tool_calls.append(m.group(1))
    except (OSError, PermissionError):
        pass
    return tool_calls


def detect_loops(tool_calls: list[str], min_repeat: int = 3, seq_length: int = 3) -> dict[tuple, int]:
    """Detect repeating sequences of tool calls.
    
    Args:
        tool_calls: List of tool call names in order
        min_repeat: Minimum repetitions to flag as a loop
        seq_length: Length of sequence to check
        
    Returns:
        Dict mapping repeating sequences to their count, sorted by frequency
    """
    sequences = Counter()
    for i in range(len(tool_calls) - seq_length + 1):
        seq = tuple(tool_calls[i:i + seq_length])
        sequences[seq] += 1
    
    loops = {seq: count for seq, count in sequences.items() if count >= min_repeat}
    return dict(sorted(loops.items(), key=lambda x: x[1], reverse=True)[:10])


def detect_single_tool_spam(tool_calls: list[str], threshold: int = 5) -> list[dict]:
    """Detect when the same tool is called repeatedly without variation.
    
    Returns list of {tool, count, start_index} for tools called >= threshold times consecutively.
    """
    spam = []
    if not tool_calls:
        return spam
    
    current_tool = tool_calls[0]
    current_count = 1
    current_start = 0
    
    for i in range(1, len(tool_calls)):
        if tool_calls[i] == current_tool:
            current_count += 1
        else:
            if current_count >= threshold:
                spam.append({
                    "tool": current_tool,
                    "count": current_count,
                    "start_index": current_start,
                })
            current_tool = tool_calls[i]
            current_count = 1
            current_start = i
    
    # Check last run
    if current_count >= threshold:
        spam.append({
            "tool": current_tool,
            "count": current_count,
            "start_index": current_start,
        })
    
    return spam


def analyze_session(audit_file: str) -> dict:
    """Analyze a session audit file for loop patterns and anomalies.
    
    Returns dict with tool_calls, loops, spam, and summary statistics.
    """
    tool_calls = extract_tool_calls(audit_file)
    loops = detect_loops(tool_calls)
    spam = detect_single_tool_spam(tool_calls)
    
    # Tool call frequency
    tool_freq = dict(Counter(tool_calls).most_common(10))
    
    # Unique tools used
    unique_tools = list(dict.fromkeys(tool_calls))  # preserve order
    
    return {
        "audit_file": os.path.basename(audit_file),
        "total_calls": len(tool_calls),
        "unique_tools": len(unique_tools),
        "tool_frequency": tool_freq,
        "loops_detected": len(loops),
        "loops": {str(seq): count for seq, count in loops.items()},
        "spam_detected": len(spam),
        "spam": spam,
        "is_stuck": len(loops) > 0 or len(spam) > 0,
    }


def scan_recent_logs(log_dir: str = "~/.local/tau/log", count: int = 10) -> list[dict]:
    """Scan recent audit logs for loop patterns.
    
    Returns list of analysis results for logs with detected issues.
    """
    log_dir = os.path.expanduser(log_dir)
    logs = sorted(
        glob.glob(os.path.join(log_dir, "*.audit")),
        reverse=True
    )[:count]
    
    results = []
    for log in logs:
        analysis = analyze_session(log)
        if analysis["is_stuck"]:
            results.append(analysis)
    
    return results


def main() -> None:
    if len(sys.argv) > 1:
        # Analyze specific file(s)
        for audit_file in sys.argv[1:]:
            analysis = analyze_session(audit_file)
            print(json.dumps(analysis, indent=2))
            if analysis["is_stuck"]:
                print(f"\n⚠️  STUCK PATTERN DETECTED in {os.path.basename(audit_file)}")
                if analysis["loops"]:
                    for seq, count in analysis["loops"].items():
                        print(f"  Loop: {seq} (x{count})")
                if analysis["spam"]:
                    for s in analysis["spam"]:
                        print(f"  Spam: {s['tool']} called {s['count']}x consecutively")
            else:
                print(f"✓ No loops detected in {os.path.basename(audit_file)}")
    else:
        # Scan recent logs
        results = scan_recent_logs()
        if results:
            print(f"Found {len(results)} log(s) with potential loops:")
            for r in results:
                print(f"\n  {r['audit_file']}: {r['total_calls']} calls, "
                      f"{r['loops_detected']} loops, {r['spam_detected']} spam patterns")
                for seq, count in r["loops"].items():
                    print(f"    Loop: {seq} (x{count})")
        else:
            print("No loop patterns detected in recent logs")


if __name__ == "__main__":
    main()
