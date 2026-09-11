"""edit_run.py — Helpers for the read→edit→run→assess cycle.

Usage:
    from skills.edit_and_run.edit_run import (
        find_problem_area, verify_edit, run_and_capture, edit_cycle
    )
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


def find_problem_area(file_path: str, error_output: str) -> list[dict]:
    """Parse error output (traceback) to find relevant file regions.

    Returns a list of dicts with keys: file, line, context.
    """
    results = []
    # Match Python traceback lines: File "path", line N, in ...
    pattern = re.compile(
        r'File\s+[\'"]([^\'"]+)[\'"]\s*,\s*line\s+(\d+)'
    )
    for match in pattern.finditer(error_output):
        matched_file = match.group(1)
        line_no = int(match.group(2))
        results.append({
            "file": matched_file,
            "line": line_no,
            "context": _get_context(matched_file, line_no),
        })
    # Also match generic "filename:line:" patterns (e.g. compiler errors)
    generic = re.compile(r'([^\s]+)\s*:\s*(\d+)\s*:')
    for match in generic.finditer(error_output):
        matched_file = match.group(1)
        line_no = int(match.group(2))
        if matched_file not in [r["file"] for r in results]:
            results.append({
                "file": matched_file,
                "line": line_no,
                "context": _get_context(matched_file, line_no),
            })
    return results


def _get_context(file_path: str, line_no: int, half: int = 5) -> str:
    """Return lines around line_no from file_path."""
    try:
        text = Path(file_path).read_text()
    except (OSError, UnicodeDecodeError):
        return f"Could not read {file_path}"
    lines = text.splitlines()
    start = max(0, line_no - half - 1)
    end = min(len(lines), line_no + half)
    result = []
    for i in range(start, end):
        marker = ">>>" if i == line_no - 1 else "   "
        result.append(f"{marker} {i + 1}: {lines[i]}")
    return "\n".join(result)


def verify_edit(file_path: str, old_text: str, new_text: str) -> dict:
    """Check that old_text exists in file before edit.

    Returns dict with 'ok' (bool), 'line' (int or None), and 'message'.
    """
    try:
        content = Path(file_path).read_text()
    except OSError as exc:
        return {"ok": False, "line": None, "message": f"Cannot read {file_path}: {exc}"}

    if old_text not in content:
        return {
            "ok": False,
            "line": None,
            "message": f"old_text not found in {file_path}",
        }

    # Find approximate line number
    line_no = content[:content.index(old_text)].count("\n") + 1
    return {
        "ok": True,
        "line": line_no,
        "message": f"old_text found at line {line_no}",
    }


def run_and_capture(cmd: str) -> dict:
    """Run a command, capture stdout/stderr, return exit code.

    Returns dict with 'stdout', 'stderr', 'returncode'.
    """
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=120
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def edit_cycle(file_path: str, old_text: str, new_text: str, test_cmd: str) -> dict:
    """Complete cycle: verify → edit → run test → return result.

    Returns dict with 'verify', 'edit', 'test' keys.
    """
    # Step 1: verify old_text exists
    verify = verify_edit(file_path, old_text)
    if not verify["ok"]:
        return {"verify": verify, "edit": None, "test": None}

    # Step 2: perform edit
    edit_result = _do_edit(file_path, old_text, new_text)

    # Step 3: run test
    test_result = run_and_capture(test_cmd)

    return {
        "verify": verify,
        "edit": edit_result,
        "test": test_result,
    }


def _do_edit(file_path: str, old_text: str, new_text: str) -> dict:
    """Replace first occurrence of old_text with new_text in file_path."""
    try:
        content = Path(file_path).read_text()
    except OSError as exc:
        return {"ok": False, "message": f"Cannot read {file_path}: {exc}"}

    if old_text not in content:
        return {"ok": False, "message": "old_text not found (race condition?)"}

    new_content = content.replace(old_text, new_text, 1)
    try:
        Path(file_path).write_text(new_content)
    except OSError as exc:
        return {"ok": False, "message": f"Cannot write {file_path}: {exc}"}

    return {"ok": True, "message": "Edit applied successfully"}
