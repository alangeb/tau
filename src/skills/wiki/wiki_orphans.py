#!/usr/bin/env python3
"""Find orphaned references (no content file points to them)."""
import argparse
import os
import re
import sys
from pathlib import Path

def find_referenced_files(wiki_dir):
    """Find all files referenced via [[path|text]] in content files."""
    referenced = set()
    ref_pattern = re.compile(r"\[\[([^\]|]+)\|")
    for root, dirs, files in os.walk(wiki_dir):
        if "/references/" in root or "/_dump/" in root:
            continue
        for f in files:
            if f.endswith(".md"):
                path = os.path.join(root, f)
                with open(path, "r") as fh:
                    content = fh.read()
                for match in ref_pattern.finditer(content):
                    ref_path = match.group(1).strip()
                    file_dir = os.path.dirname(path)
                    full_ref = os.path.normpath(os.path.join(file_dir, ref_path))
                    referenced.add(full_ref)
    return referenced

def find_reference_files(wiki_dir):
    """Find all files in references/ folder."""
    ref_dir = wiki_dir / "references"
    if not ref_dir.exists():
        return set()
    files = set()
    for root, dirs, files_list in os.walk(ref_dir):
        for f in files_list:
            files.add(os.path.join(root, f))
    return files

def main():
    parser = argparse.ArgumentParser(description="Find orphaned references")
    parser.add_argument("--wiki-dir", default=os.path.expanduser("~/.local/tau/wiki"))
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    if not wiki_dir.exists():
        print(f"ERROR: {wiki_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    referenced = find_referenced_files(wiki_dir)
    reference_files = find_reference_files(wiki_dir)

    # Orphans = reference files not referenced by any content file
    orphans = reference_files - referenced

    # Group by session folder
    orphan_folders = {}
    for orphan in orphans:
        parent = str(Path(orphan).parent)
        if parent not in orphan_folders:
            orphan_folders[parent] = []
        orphan_folders[parent].append(orphan)

    if args.json:
        result = {
            "orphans": sorted(orphans),
            "folders": orphan_folders,
            "count": len(orphans)
        }
        print(json.dumps(result, indent=2))
    else:
        if orphans:
            print(f"Found {len(orphans)} orphaned references in {len(orphan_folders)} folders:")
            for folder, files in sorted(orphan_folders.items()):
                rel = os.path.relpath(folder, wiki_dir)
                print(f"  {rel}/")
                for f in files:
                    print(f"    - {os.path.basename(f)}")
            sys.exit(1)
        else:
            print("No orphaned references found.")
            sys.exit(0)

if __name__ == "__main__":
    main()
