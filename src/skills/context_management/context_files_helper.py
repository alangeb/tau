#!/usr/bin/env python3
"""Context files helper — analyze, estimate tokens, and compress context files."""
from __future__ import annotations

import sys
from pathlib import Path


def estimate_tokens(text: str) -> dict:
    """Estimate token count from text. Returns dict with chars, words, estimated_tokens."""
    chars = len(text)
    words = len(text.split())
    # Rule of thumb: ~1 token per 4 chars, ~1.3 tokens per word; average both
    estimated = int((chars / 4 + words * 1.3) / 2)
    return {"chars": chars, "words": words, "estimated_tokens": estimated}


def analyze_file(file_path: str) -> dict:
    """Analyze a context file. Returns size, lines, token estimate, recommendations."""
    p = Path(file_path)
    if not p.exists():
        return {"error": f"File not found: {file_path}"}
    content = p.read_text(errors="replace")
    lines = content.split("\n")
    token_info = estimate_tokens(content)
    size_kb = p.stat().st_size / 1024
    result = {
        "file": str(p),
        "size_kb": round(size_kb, 1),
        "lines": len(lines),
        **token_info,
    }
    # Recommendations
    recs = []
    if size_kb > 100:
        recs.append("FILE > 100KB — consider rotation")
    if token_info["estimated_tokens"] > 50000:
        recs.append("Tokens > 50K — compress or truncate")
    if len(lines) > 2000:
        recs.append(f"Lines > 2000 — keep last 500-1000")
    result["recommendations"] = recs if recs else ["OK — no action needed"]
    return result


def compress_file(file_path: str, max_lines: int = 500) -> dict:
    """Compress a context file by keeping only the last max_lines. Returns result."""
    p = Path(file_path)
    if not p.exists():
        return {"error": f"File not found: {file_path}"}
    content = p.read_text(errors="replace")
    lines = content.split("\n")
    original = len(lines)
    if original <= max_lines:
        return {"status": "no-op", "lines": original, "message": f"Already under {max_lines} lines"}
    # Backup
    backup = Path(str(p) + ".bak")
    backup.write_text(content)
    # Truncate
    truncated = "\n".join(lines[-max_lines:])
    p.write_text(truncated)
    return {"status": "compressed", "original_lines": original, "new_lines": max_lines, "backup": str(backup)}


def main():
    if len(sys.argv) < 2:
        print("Usage: context_files_helper.py <analyze|estimate|compress> <args...>")
        print("  analyze <file>              — Analyze context file size and tokens")
        print("  estimate <text>             — Estimate tokens in text")
        print("  compress <file> [max_lines] — Compress file to max_lines (default: 500)")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "analyze" and len(sys.argv) >= 3:
        result = analyze_file(sys.argv[2])
        for k, v in result.items():
            print(f"  {k}: {v}")
    elif cmd == "estimate" and len(sys.argv) >= 3:
        result = estimate_tokens(sys.argv[2])
        for k, v in result.items():
            print(f"  {k}: {v}")
    elif cmd == "compress" and len(sys.argv) >= 3:
        max_lines = int(sys.argv[3]) if len(sys.argv) >= 4 else 500
        result = compress_file(sys.argv[2], max_lines)
        for k, v in result.items():
            print(f"  {k}: {v}")
    else:
        print(f"Unknown command or missing args: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
