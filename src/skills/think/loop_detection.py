#!/usr/bin/env python3
"""loop_detection.py — Detect stuck loops in audit logs."""
import os, re, glob
from collections import Counter, defaultdict

def detect_loops(audit_file):
    """Detect repeating tool call sequences in an audit file."""
    tool_calls = []
    with open(audit_file) as f:
        for line in f:
            m = re.search(r"final_name='(\w+)'", line)
            if m:
                tool_calls.append(m.group(1))

    # Look for repeating sequences of 3+ tool calls
    sequences = defaultdict(int)
    for i in range(len(tool_calls) - 2):
        seq = tuple(tool_calls[i:i+3])
        sequences[seq] += 1

    loops = {seq: count for seq, count in sequences.items() if count > 3}
    return dict(sorted(loops.items(), key=lambda x: x[1], reverse=True)[:5])

def analyze_session(audit_file):
    """Analyze a session for loop patterns."""
    loops = detect_loops(audit_file)
    if loops:
        print(f"Potential loops in {os.path.basename(audit_file)}:")
        for seq, count in loops.items():
            print(f"  {seq} (x{count})")
    else:
        print(f"No loops detected in {os.path.basename(audit_file)}")
    return loops

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        analyze_session(sys.argv[1])
    else:
        log_dir = os.path.expanduser("~/.local/tau/log")
        logs = sorted(glob.glob(os.path.join(log_dir, "*_2026*_1.audit")), reverse=True)[:10]
        for log in logs:
            analyze_session(log)
