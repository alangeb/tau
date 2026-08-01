#!/usr/bin/env python3
"""Validate wiki structure (INDEX.md, frontmatter, cross-refs)."""
import argparse
import os
import re
import sys
from pathlib import Path

def check_index_files(wiki_dir):
    """Check all folders have INDEX.md."""
    issues = []
    for root, dirs, files in os.walk(wiki_dir):
        # Skip special folders
        if "/references/" in root or "/_dump/" in root:
            continue
        if "INDEX.md" not in files:
            rel = os.path.relpath(root, wiki_dir)
            if rel != ".":
                issues.append(f"Missing INDEX.md: {rel}/")
    return issues

def check_frontmatter(wiki_dir):
    """Check all content files have frontmatter."""
    issues = []
    for root, dirs, files in os.walk(wiki_dir):
        if "/references/" in root or "/_dump/" in root:
            continue
        for f in files:
            if f.endswith(".md") and f != "INDEX.md":
                path = os.path.join(root, f)
                with open(path, "r") as fh:
                    content = fh.read()
                if not content.startswith("---"):
                    rel = os.path.relpath(path, wiki_dir)
                    issues.append(f"No frontmatter: {rel}")
    return issues

def check_cross_refs(wiki_dir):
    """Check all [[path|text]] refs point to existing files."""
    issues = []
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
                    # Resolve relative path
                    file_dir = os.path.dirname(path)
                    full_ref = os.path.normpath(os.path.join(file_dir, ref_path))
                    if not os.path.exists(full_ref):
                        rel = os.path.relpath(path, wiki_dir)
                        issues.append(f"Broken ref in {rel}: {ref_path}")
    return issues

def main():
    parser = argparse.ArgumentParser(description="Validate wiki structure")
    parser.add_argument("--wiki-dir", default=os.path.expanduser("~/.local/tau/wiki"))
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    if not wiki_dir.exists():
        print(f"ERROR: {wiki_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    issues = []
    issues.extend(check_index_files(wiki_dir))
    issues.extend(check_frontmatter(wiki_dir))
    issues.extend(check_cross_refs(wiki_dir))

    if args.json:
        result = {"issues": issues, "count": len(issues)}
        print(json.dumps(result, indent=2))
    else:
        if issues:
            print(f"Found {len(issues)} issues:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
        else:
            print("Wiki structure valid. No issues found.")
            sys.exit(0)

if __name__ == "__main__":
    main()
