#!/usr/bin/env python3
"""Batch edit files matching a pattern."""
import sys, os, re, glob as glob_mod

def find_files(path, pattern):
    """Find files containing pattern."""
    files = []
    for root, dirs, filenames in os.walk(path):
        # Skip hidden and cache dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'node_modules', 'venv')]
        for f in filenames:
            if f.endswith('.py'):
                fp = os.path.join(root, f)
                try:
                    with open(fp) as fh:
                        if pattern in fh.read():
                            files.append(fp)
                except: pass
    return files

def replace_in_file(filepath, old, new, dry_run=True):
    """Replace old with new in file."""
    try:
        with open(filepath) as f:
            content = f.read()
        if old not in content:
            return 0
        count = content.count(old)
        if not dry_run:
            with open(filepath, 'w') as f:
                f.write(content.replace(old, new))
        return count
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return 0

def main():
    if len(sys.argv) < 4:
        print("Usage: bulk_edit.py 'pattern' 'old' 'new' [path]")
        sys.exit(1)
    
    pattern = sys.argv[1]
    old = sys.argv[2]
    new = sys.argv[3]
    path = sys.argv[4] if len(sys.argv) > 4 else '.'
    
    files = find_files(path, old)
    print(f"Found {len(files)} files containing '{old}':")
    
    total = 0
    for f in files:
        count = replace_in_file(f, old, new, dry_run=True)
        if count > 0:
            print(f"  {f}: {count} occurrences")
            total += count
    
    print(f"\nTotal: {total} replacements across {len(files)} files")
    print("Run with --apply to make changes")

if __name__ == '__main__':
    main()
