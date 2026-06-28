#!/usr/bin/env python3
"""SWE-bench artifact checker — shows test results summary."""
import os, sys, glob, json

def main():
    base = os.environ.get("ARTIFACT_BASE", "artifacts")
    if not os.path.isdir(base):
        print(f"No artifacts dir at {base}")
        return 1
    
    tests = sorted(glob.glob(os.path.join(base, "*/")))
    if not tests:
        print("No test artifacts found")
        return 0
    
    results = []
    for t in tests:
        test_id = os.path.basename(t.rstrip("/"))
        status_file = os.path.join(t, "eval", "status.json")
        status = "no-eval"
        if os.path.exists(status_file):
            try:
                with open(status_file) as f:
                    data = json.load(f)
                status = data.get("status", "unknown")
            except:
                status = "read-error"
        
        has_patch = bool(glob.glob(os.path.join(t, "fix", "*.patch")))
        has_audit = bool(glob.glob(os.path.join(t, "fix", "*.audit")))
        
        results.append((test_id, status, has_patch, has_audit))
    
    passed = sum(1 for _, s, _, _ in results if s == "PASS")
    failed = sum(1 for _, s, _, _ in results if s == "FAIL")
    no_eval = sum(1 for _, s, _, _ in results if s == "no-eval")
    
    print(f"Tests: {len(results)} (PASS={passed} FAIL={failed} no-eval={no_eval})")
    print(f"{'Test':<20} {'Status':<10} {'Patch':<6} {'Audit':<6}")
    for test_id, status, has_patch, has_audit in results:
        print(f"{test_id:<20} {status:<10} {'✓' if has_patch else '✗':<6} {'✓' if has_audit else '✗':<6}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
