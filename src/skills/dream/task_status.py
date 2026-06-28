#!/usr/bin/env python3
"""Dream task status checker — shows pending/active tasks."""
import os, sys, glob

def main():
    base = os.environ.get("TASK_BASE", "tasks")
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
    if os.path.exists("dream.stop"):
        print("WARNING: dream.stop file exists — loop halted")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
