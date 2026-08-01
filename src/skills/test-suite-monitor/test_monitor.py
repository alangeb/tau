#!/usr/bin/env python3
"""Test suite monitor helper — parse, track, and compare test results."""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter
from pathlib import Path


def parse_test_results(test_dir: str = "$HOME/tau/test") -> dict:
    """Parse all status.json files in test output directory.
    
    Returns dict with counts by status and per-test details.
    """
    test_dir = os.path.expanduser(test_dir)
    results = {"PASS": 0, "FAIL": 0, "ERROR": 0, "SKIP": 0, "UNKNOWN": 0, "TOTAL": 0}
    details: list[dict] = []
    
    status_files = glob.glob(os.path.join(test_dir, "output", "*", "status.json"))
    for f in status_files:
        try:
            with open(f) as fh:
                data = json.load(fh)
                status = data.get("status", "UNKNOWN")
                test_name = os.path.basename(os.path.dirname(f))
                results["TOTAL"] += 1
                results[status] = results.get(status, 0) + 1
                details.append({
                    "test": test_name,
                    "status": status,
                    "message": data.get("message", ""),
                    "duration": data.get("duration", ""),
                })
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            results["TOTAL"] += 1
            results["ERROR"] += 1
            details.append({"test": os.path.basename(os.path.dirname(f)), "status": "ERROR"})
    
    results["details"] = details
    return results


def print_summary(test_dir: str = "$HOME/tau/test") -> None:
    """Print formatted test results summary."""
    results = parse_test_results(test_dir)
    total = results["TOTAL"]
    passed = results["PASS"]
    failed = results["FAIL"]
    errors = results["ERROR"]
    skipped = results.get("SKIP", 0)
    unknown = results.get("UNKNOWN", 0)
    
    print(f"Tests: {total} | PASS: {passed} | FAIL: {failed} | ERROR: {errors}", end="")
    if skipped:
        print(f" | SKIP: {skipped}", end="")
    if unknown:
        print(f" | UNKNOWN: {unknown}", end="")
    print()
    
    if total > 0:
        pct = (passed / total) * 100
        print(f"Pass rate: {pct:.1f}%")
    
    # Show failed tests
    failed_tests = [d for d in results.get("details", []) if d["status"] in ("FAIL", "ERROR")]
    if failed_tests:
        print(f"\nFailed ({len(failed_tests)}):")
        for t in failed_tests[:20]:
            msg = f" — {t['message']}" if t.get("message") else ""
            print(f"  ❌ {t['test']}{msg}")


def compare_runs(dir1: str, dir2: str) -> dict:
    """Compare test results between two runs.
    
    Returns dict with improved, regressed, new_failures, and new_passes.
    """
    r1 = parse_test_results(dir1)
    r2 = parse_test_results(dir2)
    
    # Build status maps
    s1 = {d["test"]: d["status"] for d in r1.get("details", [])}
    s2 = {d["test"]: d["status"] for d in r2.get("details", [])}
    
    all_tests = set(s1.keys()) | set(s2.keys())
    
    comparison = {
        "run1_total": r1["TOTAL"],
        "run2_total": r2["TOTAL"],
        "run1_pass_rate": round(r1["PASS"] / r1["TOTAL"] * 100, 1) if r1["TOTAL"] > 0 else 0,
        "run2_pass_rate": round(r2["PASS"] / r2["TOTAL"] * 100, 1) if r2["TOTAL"] > 0 else 0,
        "improved": [],
        "regressed": [],
        "new_tests": [],
    }
    
    for test in sorted(all_tests):
        status1 = s1.get(test, "MISSING")
        status2 = s2.get(test, "MISSING")
        
        if status1 == "MISSING" and status2 != "MISSING":
            comparison["new_tests"].append(test)
        elif status1 != status2:
            if status1 in ("FAIL", "ERROR") and status2 == "PASS":
                comparison["improved"].append(test)
            elif status1 == "PASS" and status2 in ("FAIL", "ERROR"):
                comparison["regressed"].append(test)
    
    return comparison


def print_comparison(dir1: str, dir2: str) -> None:
    """Print formatted comparison between two test runs."""
    cmp = compare_runs(dir1, dir2)
    
    print(f"=== Test Run Comparison ===")
    print(f"Run 1: {cmp['run1_total']} tests, {cmp['run1_pass_rate']}% pass")
    print(f"Run 2: {cmp['run2_total']} tests, {cmp['run2_pass_rate']}% pass")
    
    delta = cmp["run2_pass_rate"] - cmp["run1_pass_rate"]
    if delta > 0:
        print(f"Change: +{delta:.1f}% ✓")
    elif delta < 0:
        print(f"Change: {delta:.1f}% ⚠️")
    else:
        print("Change: No change")
    
    if cmp["improved"]:
        print(f"\nImproved ({len(cmp['improved'])}):")
        for t in cmp["improved"]:
            print(f"  ✓ {t}")
    
    if cmp["regressed"]:
        print(f"\nRegressed ({len(cmp['regressed'])}):")
        for t in cmp["regressed"]:
            print(f"  ❌ {t}")
    
    if cmp["new_tests"]:
        print(f"\nNew tests ({len(cmp['new_tests'])}):")
        for t in cmp["new_tests"]:
            print(f"  + {t}")


def main() -> None:
    if len(sys.argv) < 2:
        test_dir = sys.argv[1] if len(sys.argv) > 1 else "$HOME/tau/test"
        print_summary(test_dir)
        return
    
    cmd = sys.argv[1]
    if cmd == "summary":
        test_dir = sys.argv[2] if len(sys.argv) > 2 else "$HOME/tau/test"
        print_summary(test_dir)
    elif cmd == "json":
        test_dir = sys.argv[2] if len(sys.argv) > 2 else "$HOME/tau/test"
        print(json.dumps(parse_test_results(test_dir), indent=2))
    elif cmd == "compare":
        dir1 = sys.argv[2] if len(sys.argv) > 2 else "$HOME/tau/test"
        dir2 = sys.argv[3] if len(sys.argv) > 3 else ""
        if not dir2:
            print("Usage: test_monitor.py compare <dir1> <dir2>")
            sys.exit(1)
        print_comparison(dir1, dir2)
    else:
        print(f"Usage: {sys.argv[0]} {{summary|json|compare}} [args...]")
        sys.exit(1)


if __name__ == "__main__":
    main()
