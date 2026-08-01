#!/usr/bin/env python3
"""Code review helper — static analysis, checklist runner, and report generation."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REVIEW_CHECKLIST = [
    "Correctness — logic, edge cases, error handling",
    "Clarity — naming, structure, readability",
    "Conciseness — no redundancy, no dead code",
    "Documentation — docstrings, comments, type hints",
    "Location — right module, right function",
    "Usage — called correctly, no unused imports",
]


def generate_review_checklist(path: str = ".") -> str:
    """Generate a markdown review checklist for a path."""
    lines = [f"# Review Checklist for {path}", ""]
    for i, item in enumerate(REVIEW_CHECKLIST, 1):
        lines.append(f"- [ ] {item}")
    return "\n".join(lines)


def review_summary(filename: str, items: int, critical: int, rating: float) -> str:
    """Generate review summary line."""
    return f"=== CODE REVIEW: {filename} ===\nTotal: {items} | Critical: {critical} | Rating: {rating}/10"


def run_pre_analysis(path: str = ".") -> dict:
    """Run pyscan and pyanalyze via subprocess and return structured results."""
    result: dict = {"pyscan": None, "pyanalyze": None, "errors": []}
    
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pyscan", "--compact", path],
            capture_output=True, text=True, timeout=30
        )
        result["pyscan"] = r.stdout.strip() if r.returncode == 0 else r.stderr.strip()
    except Exception as e:
        result["errors"].append(f"pyscan: {e}")
    
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pyanalyze", path],
            capture_output=True, text=True, timeout=30
        )
        result["pyanalyze"] = r.stdout.strip() if r.returncode == 0 else r.stderr.strip()
    except Exception as e:
        result["errors"].append(f"pyanalyze: {e}")
    
    return result


def scan_file_for_issues(filepath: str) -> list[dict]:
    """Scan a Python file for common issues using regex-based static analysis.
    
    Returns list of {line, issue, severity} dicts.
    """
    issues: list[dict] = []
    path = Path(filepath)
    if not path.exists():
        return [{"line": 0, "issue": "File not found", "severity": "error"}]
    
    content = path.read_text()
    lines = content.split("\n")
    
    for i, line in enumerate(lines, 1):
        # Long lines (>120 chars)
        if len(line) > 120:
            issues.append({"line": i, "issue": f"Line too long ({len(line)} chars)", "severity": "low"})
        
        # Function without docstring (check next non-empty line)
        if re.match(r'\s*def\s+\w+\s*\(', line):
            for j in range(i, min(i + 3, len(lines))):
                if lines[j].strip() and not lines[j].strip().startswith('#'):
                    if not re.match(r'\s*(\"\"\'\'|"""|\'\'\')', lines[j]):
                        issues.append({"line": i, "issue": "Missing docstring", "severity": "medium"})
                    break
        
        # TODO/FIXME markers
        if re.search(r'\b(TODO|FIXME|HACK|XXX)\b', line, re.IGNORECASE):
            issues.append({"line": i, "issue": f"Marker found: {line.strip()}", "severity": "info"})
        
        # Bare except
        if re.match(r'\s*except\s*:', line):
            issues.append({"line": i, "issue": "Bare except clause", "severity": "high"})
        
        # print statements (not in __main__)
        if re.search(r'\bprint\s*\(', line) and 'if __name__' not in content[:content.index(line) if line in content else 0]:
            issues.append({"line": i, "issue": "print() statement", "severity": "low"})
    
    return issues


def generate_review_report(path: str) -> str:
    """Generate a full review report following the SKILL.md format."""
    report_parts = [f"=== CODE REVIEW: {path} ===", ""]
    
    # Pre-analysis
    report_parts.append("## Pre-Analysis")
    analysis = run_pre_analysis(path)
    if analysis.get("pyscan"):
        report_parts.append(f"- pyscan: {analysis['pyscan'][:200]}...")
    if analysis.get("pyanalyze"):
        report_parts.append(f"- pyanalyze: {analysis['pyanalyze'][:200]}...")
    report_parts.append("")
    
    # File issues
    report_parts.append("## Issues Found")
    p = Path(path)
    if p.is_file():
        issues = scan_file_for_issues(str(p))
        for issue in issues[:20]:  # Limit output
            report_parts.append(f"- L{issue['line']} [{issue['severity']}]: {issue['issue']}")
    elif p.is_dir():
        for pyfile in sorted(p.glob("*.py"))[:5]:
            issues = scan_file_for_issues(str(pyfile))
            if issues:
                report_parts.append(f"\n### {pyfile.name}")
                for issue in issues[:5]:
                    report_parts.append(f"- L{issue['line']} [{issue['severity']}]: {issue['issue']}")
    report_parts.append("")
    
    # Checklist
    report_parts.append(generate_review_checklist(path))
    report_parts.append("")
    
    # Summary
    all_issues = scan_file_for_issues(str(p)) if p.is_file() else []
    critical = sum(1 for i in all_issues if i["severity"] in ("high", "error"))
    total = len(all_issues)
    rating = max(0, 10 - critical * 2 - sum(1 for i in all_issues if i["severity"] == "medium") * 0.5)
    report_parts.append(review_summary(path, total, critical, round(rating, 1)))
    
    return "\n".join(report_parts)


def main() -> None:
    if len(sys.argv) < 2:
        print(generate_review_checklist())
        return
    
    cmd = sys.argv[1]
    if cmd == "checklist":
        print(generate_review_checklist(sys.argv[2] if len(sys.argv) > 2 else "."))
    elif cmd == "analyze":
        path = sys.argv[2] if len(sys.argv) > 2 else "."
        print(json.dumps(run_pre_analysis(path), indent=2))
    elif cmd == "check":
        filepath = sys.argv[2] if len(sys.argv) > 2 else "."
        print(json.dumps(scan_file_for_issues(filepath), indent=2))
    elif cmd == "report":
        path = sys.argv[2] if len(sys.argv) > 2 else "."
        print(generate_review_report(path))
    else:
        print(f"Usage: {sys.argv[0]} {{checklist|analyze|check|report}} [path]")
        sys.exit(1)


if __name__ == "__main__":
    main()
