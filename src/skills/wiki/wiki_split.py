#!/usr/bin/env python3
"""Find oversized files (> 5kb). Detector only — LLM does splitting."""
import argparse
import json
import os
import sys
from pathlib import Path

SIZE_LIMIT = 5 * 1024  # 5kb

def find_oversized(wiki_dir):
    """Find content files exceeding size limit."""
    oversized = []
    for root, dirs, files in os.walk(wiki_dir):
        if "/references/" in root or "/_dump/" in root:
            continue
        for f in files:
            if f.endswith(".md"):
                path = os.path.join(root, f)
                size = os.path.getsize(path)
                if size > SIZE_LIMIT:
                    rel = os.path.relpath(path, wiki_dir)
                    oversized.append({"path": rel, "size": size})
    return oversized

def main():
    parser = argparse.ArgumentParser(description="Find oversized wiki files")
    parser.add_argument("--wiki-dir", default=os.path.expanduser("~/.local/tau/wiki"))
    parser.add_argument("--limit", type=int, default=SIZE_LIMIT, help="Size limit in bytes (default: 5120)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    if not wiki_dir.exists():
        print(f"ERROR: {wiki_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    oversized = find_oversized(wiki_dir)

    if args.json:
        result = {"oversized": oversized, "count": len(oversized), "limit": args.limit}
        print(json.dumps(result, indent=2))
    else:
        if oversized:
            print(f"Found {len(oversized)} oversized files (>{args.limit} bytes):")
            for f in oversized:
                print(f"  {f['path']} ({f['size']} bytes)")
            sys.exit(1)
        else:
            print(f"No oversized files found (limit: {args.limit} bytes).")
            sys.exit(0)

if __name__ == "__main__":
    main()
