#!/usr/bin/env python3
"""analyze.py — Quick Python project analysis: files, functions, classes, __init__.py gaps."""
import sys, os, ast, json
from pathlib import Path

def analyze(path="."):
    """Analyze a Python project directory."""
    root = Path(path).resolve()
    if not root.is_dir():
        print(f"ERROR: {path} is not a directory", file=sys.stderr)
        sys.exit(1)
    py_files = sorted(root.rglob("*.py"))
    # Exclude common dirs
    exclude = {"__pycache__", ".venv", "venv", "node_modules", ".git", ".tox", ".eggs"}
    py_files = [f for f in py_files if not any(p in f.parts for p in exclude)]
    stats = {"files": len(py_files), "total_loc": 0, "functions": 0, "classes": 0, "imports": 0}
    init_gaps = []
    for f in py_files:
        rel = f.relative_to(root)
        stats["total_loc"] += f.stat().st_size // 4  # rough estimate
        # Check for __init__.py gaps
        parent = f.parent
        if parent != root and not (parent / "__init__.py").exists():
            init_gaps.append(str(parent.relative_to(root)))
        # Parse AST for counts
        try:
            tree = ast.parse(f.read_text(), str(f))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    stats["functions"] += 1
                elif isinstance(node, ast.ClassDef):
                    stats["classes"] += 1
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    stats["imports"] += 1
        except (SyntaxError, UnicodeDecodeError):
            pass
    return stats, sorted(set(init_gaps))

def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: analyze.py [DIR] [--json]")
        print("  Quick Python project analysis: count files, functions, classes.")
        print("  DIR        Directory to analyze (default: .)")
        print("  --json     Output as JSON")
        sys.exit(0)
    path = sys.argv[-1] if len(sys.argv) > 1 else "."
    as_json = "--json" in sys.argv
    stats, gaps = analyze(path)
    if as_json:
        print(json.dumps({"stats": stats, "init_gaps": gaps}, indent=2))
    else:
        print(f"=== Python Project Analysis: {path} ===")
        print(f"  Files:    {stats['files']}")
        print(f"  Functions: {stats['functions']}")
        print(f"  Classes:  {stats['classes']}")
        print(f"  Imports:  {stats['imports']}")
        if gaps:
            print(f"\n  __init__.py gaps ({len(gaps)}):")
            for g in gaps[:10]:
                print(f"    {g}/")
            if len(gaps) > 10:
                print(f"    ... and {len(gaps) - 10} more")
    sys.exit(0)

if __name__ == "__main__":
    main()
