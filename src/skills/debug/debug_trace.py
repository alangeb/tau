#!/usr/bin/env python3
"""Parse Python tracebacks — extract file, line, function, error type."""
import re
import sys
from pathlib import Path


def parse_traceback(text):
    """Parse traceback text, return structured info."""
    lines = text.strip().split("\n")
    result = {
        "error_type": None,
        "error_message": None,
        "frames": [],
        "file_line_pairs": []
    }
    current_frame = {}
    for line in lines:
        # Match file/line pattern
        m = re.match(r'File "([^"]+)", line (\d+)(?:, in (\w+))?', line)
        if m:
            if current_frame:
                result["frames"].append(current_frame)
            current_frame = {
                "file": m.group(1),
                "line": int(m.group(2)),
                "function": m.group(3) or None
            }
            result["file_line_pairs"].append((m.group(1), int(m.group(2))))
            continue
        # Match code line
        m = re.match(r'^\s+(\S.*)$', line)
        if m and current_frame:
            current_frame["code"] = m.group(1).strip()
            continue
        # Match error type
        m = re.match(r'^(\w+Error|\w+Exception):(.*)$', line)
        if m:
            result["error_type"] = m.group(1)
            result["error_message"] = m.group(2).strip()
    if current_frame:
        result["frames"].append(current_frame)
    return result

def main():
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text()
    else:
        text = sys.stdin.read()
    result = parse_traceback(text)
    if result["error_type"]:
        print(f"Error: {result['error_type']}: {result['error_message']}")
    if result["file_line_pairs"]:
        print(f"\nKey locations ({len(result['file_line_pairs'])} frames):")
        for f, l in result["file_line_pairs"][-5:]:  # Last 5 frames
            print(f"  {f}:{l}")

if __name__ == "__main__":
    main()
