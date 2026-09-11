#!/usr/bin/env python3
"""Dream task status checker — shows pending/active tasks."""
import glob
import os
import sys

def main():
    _script_dir = os.path.dirname(os.path.realpath(__file__))
    _root = os.path.dirname(os.path.dirname(os.path.dirname(_script_dir)))
    base = os.environ.get("TASK_BASE", os.path.join(_root, "tasks"))
    counts = {}
    for d in ["1_todo", "2_inprogress", "3_done", "3_failed"]:
        path = os.path.join(base, d)
        files = glob.glob(os.path.join(path, "*.md"))
        counts[d] = len(files)
        if files and len(files) <= 5:
            for f in sorted(files):
                print(f"  {d}: {os.path.basename(f)}")
    
    total = sum(counts.values())
    print(f"\nSummary: todo={counts['1_todo']} active={counts['2_inprogress']} done={counts['3_done']} failed={counts['3_failed']} total={total}")
    
    # Check for dream.stop
    stop_file = os.path.join(_root, "dream.stop")
    if os.path.exists(stop_file):
        print("WARNING: dream.stop file exists — loop halted")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
