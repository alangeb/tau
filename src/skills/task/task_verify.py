#!/usr/bin/env python3
"""Task verification helper — search for task implementation by content."""
import os, sys, subprocess, glob

def search_pattern(pattern, paths):
    """Search for pattern in given paths."""
    args = ["grep", "-r", pattern] + paths
    r = subprocess.run(args, capture_output=True, text=True)
    return r.stdout.strip().split("\n") if r.stdout.strip() else []

def verify_task(task_file):
    """Read task file and search for implementation."""
    if not os.path.exists(task_file):
        print(f"Task file not found: {task_file}")
        return 1
    
    with open(task_file) as f:
        content = f.read()
    
    # Extract function/class names from task description
    import re
    funcs = set(re.findall(r'def\s+(\w+)', content))
    classes = set(re.findall(r'class\s+(\w+)', content))
    
    print(f"Task: {os.path.basename(task_file)}")
    print(f"Searching for: funcs={funcs}, classes={classes}")
    
    found = 0
    all_targets = funcs | classes
    for name in all_targets:
        results = search_pattern(name, ["src/"])
        if results:
            found += 1
            print(f"  ✓ {name}: found in {len(results)} locations")
            for r in results[:3]:
                print(f"    {r[:100]}")
        else:
            print(f"  ✗ {name}: NOT FOUND")
    
    # Check tests
    test_patterns = [f"test_{n}" for n in all_targets]
    for tp in test_patterns:
        results = search_pattern(tp, ["src/tests/", "tests/"])
        if results:
            print(f"  ✓ test_{tp}: found")
    
    pct = int(found * 100 / max(len(all_targets), 1))
    print(f"\nCoverage: {found}/{len(all_targets)} ({pct}%)")
    return 0 if pct >= 50 else 1

def main():
    if len(sys.argv) < 2:
        # List all tasks
        for d in ["1_todo", "2_inprogress", "3_done", "3_failed"]:
            tasks = glob.glob(os.path.join("tasks", d, "*.md"))
            if tasks:
                print(f"{d}: {len(tasks)} tasks")
        return 0
    
    return verify_task(sys.argv[1])

if __name__ == "__main__":
    sys.exit(main())
