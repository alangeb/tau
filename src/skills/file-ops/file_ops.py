#!/usr/bin/env python3
"""File operations helper — batch file utilities."""
import os, sys, glob as glob_mod

def find_files(path: str = ".", pattern: str = "*") -> list[str]:
    """Find files matching pattern."""
    return sorted(glob_mod.glob(os.path.join(path, "**", pattern), recursive=True))

def file_stats(path: str = ".") -> dict:
    """Quick directory stats."""
    files = find_files(path)
    total_lines = 0
    total_size = 0
    for f in files:
        if os.path.isfile(f):
            with open(f) as fh:
                total_lines += sum(1 for _ in fh)
            total_size += os.path.getsize(f)
    return {"files": len(files), "lines": total_lines, "bytes": total_size}

def verify_file(path: str, expected_content: str | None = None) -> dict:
    """Verify file exists and optionally check content."""
    exists = os.path.exists(path)
    result = {"exists": exists, "size": 0, "lines": 0, "contains": False}
    if exists:
        with open(path) as f:
            content = f.read()
        result["size"] = len(content)
        result["lines"] = content.count("\n") + 1
        if expected_content:
            result["contains"] = expected_content in content
    return result

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    print(file_stats(path))