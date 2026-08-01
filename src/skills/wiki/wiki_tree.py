#!/usr/bin/env python3
"""Walk wiki tree, report stats (file counts, sizes, structure)."""
import argparse
import json
import os
import sys
from pathlib import Path

def walk_tree(wiki_dir):
    """Walk wiki directory and collect stats."""
    stats = {
        "wiki_dir": str(wiki_dir),
        "folders": [],
        "files": [],
        "total_size": 0,
        "file_count": 0,
        "folder_count": 0,
    }

    for root, dirs, files in os.walk(wiki_dir):
        rel_root = os.path.relpath(root, wiki_dir)
        if rel_root == ".":
            rel_root = ""

        # Add folder
        if rel_root:
            stats["folders"].append(rel_root)
            stats["folder_count"] += 1

        # Add files
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, wiki_dir)
            size = os.path.getsize(full_path)
            stats["files"].append({"path": rel_path, "size": size})
            stats["total_size"] += size
            stats["file_count"] += 1

    stats["total_size_mb"] = round(stats["total_size"] / (1024 * 1024), 2)
    return stats

def main():
    parser = argparse.ArgumentParser(description="Walk wiki tree, report stats")
    parser.add_argument("--wiki-dir", default=os.path.expanduser("~/.local/tau/wiki"))
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    if not wiki_dir.exists():
        print(f"ERROR: {wiki_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    stats = walk_tree(wiki_dir)

    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print(f"Wiki: {wiki_dir}")
        print(f"Folders: {stats['folder_count']}")
        print(f"Files: {stats['file_count']}")
        print(f"Total size: {stats['total_size_mb']} MB")
        print()
        print("Structure:")
        for folder in sorted(stats["folders"]):
            folder_files = [f for f in stats["files"] if f["path"].startswith(folder)]
            print(f"  {folder}/ ({len(folder_files)} files)")
            for f in folder_files[:5]:  # Show first 5 files
                print(f"    - {f['path']} ({f['size']} bytes)")
            if len(folder_files) > 5:
                print(f"    ... and {len(folder_files) - 5} more")

if __name__ == "__main__":
    main()
