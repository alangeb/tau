#!/usr/bin/env python3
"""audit_deps.py — Audit Python dependencies.
Usage: python3 skills/security-audit/audit_deps.py [requirements_file]
"""
import sys, subprocess, os
from pathlib import Path

def audit(req_file="requirements.txt"):
    print(f"=== Dependency Audit: {req_file} ===\n")
    
    # pip check
    print("--- pip check (conflicts) ---")
    result = subprocess.run(["pip", "check"], capture_output=True, text=True)
    print(result.stdout or "No conflicts found")
    
    # pip list --outdated
    print("\n--- Outdated packages ---")
    result = subprocess.run(["pip", "list", "--outdated", "--format=columns"], 
                          capture_output=True, text=True)
    print(result.stdout or "All packages up to date")
    
    # Count requirements
    if Path(req_file).exists():
        lines = [l.strip() for l in Path(req_file).read_text().split('\n') 
                 if l.strip() and not l.startswith('#')]
        print(f"\n--- Requirements: {len(lines)} packages ---")
    
    return True

if __name__ == '__main__':
    req = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"
    audit(req)
