#!/usr/bin/env python3
"""grep_structured.py — Structured grep with JSON output.
Usage: python3 skills/grep_tool/grep_structured.py <pattern> [dir] [--json]

Features:
  - Recursive search with exclusion patterns
  - JSON output for programmatic use
  - Count mode, context mode, line mode
  - Regex support
"""
import sys
import re
import os
import json
from pathlib import Path

# Default exclusions
EXCLUDE_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.mypy_cache', '.pytest_cache'}
EXCLUDE_EXTS = {'.pyc', '.pyo', '.so', '.o', '.a', '.dylib', '.dll', '.exe', '.png', '.jpg', '.gif', '.ico', '.woff', '.ttf'}


def grep_search(pattern, directory='.', recursive=True, case_sensitive=False, context=0, count=False, json_output=False):
    """Search for pattern in files."""
    dir_path = Path(directory).resolve()
    results = []
    
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error:
        print(f"Invalid regex: {pattern}", file=sys.stderr)
        sys.exit(1)
    
    def search_file(filepath):
        try:
            content = filepath.read_text(encoding='utf-8', errors='replace')
        except (PermissionError, IsADirectoryError):
            return
        
        lines = content.split('\n')
        matches = []
        
        for i, line in enumerate(lines):
            if regex.search(line):
                matches.append(i)
        
        if not matches:
            return
        
        if count:
            results.append({
                'file': str(filepath),
                'count': len(matches)
            })
        else:
            for i in matches:
                start = max(0, i - context)
                end = min(len(lines), i + context + 1)
                context_lines = lines[start:end]
                results.append({
                    'file': str(filepath),
                    'line': i + 1,
                    'match': lines[i].strip(),
                    'context': context_lines if context > 0 else None
                })
    
    if recursive:
        for root, dirs, files in os.walk(dir_path):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for fname in files:
                fpath = Path(root) / fname
                if fpath.suffix in EXCLUDE_EXTS:
                    continue
                search_file(fpath)
    else:
        if dir_path.is_file():
            search_file(dir_path)
        else:
            for f in dir_path.iterdir():
                if f.is_file() and f.suffix not in EXCLUDE_EXTS:
                    search_file(f)
    
    if json_output:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            if count:
                print(f"{r['count']:5d} {r['file']}")
            elif r.get('context'):
                print(f"\n{r['file']}:{r['line']}")
                for i, line in enumerate(r['context']):
                    line_num = r['line'] - context + i
                    marker = '>>>' if line_num == r['line'] else '   '
                    print(f"{marker} {line_num}: {line}")
            else:
                print(f"{r['file']}:{r['line']}: {r['match']}")
    
    return results


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    pattern = sys.argv[1]
    directory = sys.argv[2] if len(sys.argv) > 2 else '.'
    
    case_sensitive = '--case-sensitive' in sys.argv or '-F' in sys.argv
    context = 0
    count = False
    json_output = False
    
    if '--context' in sys.argv or '-C' in sys.argv:
        idx = sys.argv.index('--context' if '--context' in sys.argv else '-C')
        context = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 3
    
    if '--count' in sys.argv or '-c' in sys.argv:
        count = True
    
    if '--json' in sys.argv:
        json_output = True
    
    grep_search(pattern, directory, case_sensitive=case_sensitive, context=context, count=count, json_output=json_output)


if __name__ == "__main__":
    main()
