#!/usr/bin/env python3
"""release_check.py — Verify release readiness.
Usage: python3 skills/release_management/release_check.py [version]
"""
import sys, os, subprocess, re
from pathlib import Path

def check(version=None):
    issues = []
    
    # Check for CHANGELOG.md
    if not Path("CHANGELOG.md").exists():
        issues.append("CHANGELOG.md missing")
    
    # Check git status
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if result.stdout.strip():
        issues.append("Uncommitted changes")
    
    # Check for version in common files
    version_files = ["setup.py", "pyproject.toml", "package.json", "VERSION"]
    for vf in version_files:
        if Path(vf).exists():
            content = Path(vf).read_text()
            if version and version not in content:
                issues.append(f"Version {version} not in {vf}")
    
    # Run tests (if sanity.sh exists)
    if Path("sanity.sh").exists():
        print("Run: bash sanity.sh (manual)")
    
    if issues:
        print("Issues:")
        for i in issues:
            print(f"  ✗ {i}")
        return False
    print("✓ Release ready")
    return True

if __name__ == '__main__':
    version = sys.argv[1] if len(sys.argv) > 1 else None
    check(version)
