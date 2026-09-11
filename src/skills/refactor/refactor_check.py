#!/usr/bin/env python3
"""Refactor impact analysis — find all references to a symbol before refactoring."""
import ast
import sys
from pathlib import Path


def find_symbol_refs(symbol, src_dir="."):
    """Find all references to a symbol in Python files."""
    refs = []
    for pyfile in Path(src_dir).rglob("*.py"):
        try:
            content = pyfile.read_text()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == symbol:
                    if isinstance(node.ctx, ast.Load):
                        kind = "read"
                    elif isinstance(node.ctx, ast.Store):
                        kind = "write"
                    elif isinstance(node.ctx, ast.Del):
                        kind = "delete"
                    else:
                        kind = "unknown"
                    refs.append((str(pyfile), node.lineno, kind))
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == symbol:
                    refs.append((str(pyfile), node.lineno, "definition"))
        except (SyntaxError, UnicodeDecodeError):
            pass
    return refs

def main():
    if len(sys.argv) < 2:
        print("Usage: refactor_check.py <symbol> [src_dir]")
        sys.exit(1)
    symbol = sys.argv[1]
    src_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    refs = find_symbol_refs(symbol, src_dir)
    if not refs:
        print(f"No references found for '{symbol}'")
        return
    print(f"References to '{symbol}': {len(refs)}")
    for f, line, kind in sorted(refs):
        print(f"  {f}:{line} ({kind})")

if __name__ == "__main__":
    main()
