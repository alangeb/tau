"""Python import checker — catches NameError bugs before runtime."""

from __future__ import annotations

from tools import ToolContext, ToolMetadata

import ast
import builtins
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_core import TauErgon

# ── Tool metadata ────────────────────────────────────────────────

metadata = ToolMetadata(
    name="pycheck",
    description=(
        "Check Python files for missing imports causing NameError and unused imports. "
        "Cannot detect dynamic names or type-hint-only imports."
    ),
    max_size=65536,
)

# ── Args schema ──────────────────────────────────────────────────

@dataclass
class Args:
    path: str = field(metadata={"description": "File or directory to check"})
    check_missing: bool = field(default=True, metadata={"description": "Check for missing imports"})
    check_unused: bool = field(default=True, metadata={"description": "Check for unused imports"})
    output_format: str = field(default="markdown", metadata={"description": "Output format (markdown/json)"})



# ── AST helpers ──────────────────────────────────────────────────

def _get_imports(tree: ast.AST) -> set[str]:
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Add the module name (e.g., "os" from "import os")
                imports.add(alias.name.split(".")[0])
                # Add the alias name if it's different (e.g., "pd" from "import pandas as pd")
                if alias.asname:
                    imports.add(alias.asname)
        elif isinstance(node, ast.ImportFrom) and node.module:
            # Skip __future__ imports — they're special and never "used" as names
            if node.module == "__future__":
                continue
            # Add each imported name (e.g., "echo" from "from agent_console import echo")
            # Do NOT add the module name — it's the source of the import, not a used name.
            # Adding only the module name caused false "missing import" and "unused import"
            # reports for every `from X import Y` statement.
            for alias in node.names:
                if alias.name == "*":
                    continue  # Skip wildcard imports
                if alias.asname:
                    imports.add(alias.asname)
                else:
                    imports.add(alias.name)
    return imports


def _get_names(tree: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def _get_defined_names(tree: ast.AST) -> set[str]:
    defined: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined.add(node.name)
            # Collect all function arguments as defined names
            for arg in node.args.args:
                defined.add(arg.arg)
            for arg in node.args.posonlyargs:
                defined.add(arg.arg)
            for arg in node.args.kwonlyargs:
                defined.add(arg.arg)
            if node.args.vararg:
                defined.add(node.args.vararg.arg)
            if node.args.kwarg:
                defined.add(node.args.kwarg.arg)
        elif isinstance(node, ast.ClassDef):
            defined.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defined.add(node.target.id)
        elif isinstance(node, ast.Lambda):
            for arg in node.args.args:
                defined.add(arg.arg)
            for arg in node.args.posonlyargs:
                defined.add(arg.arg)
            for arg in node.args.kwonlyargs:
                defined.add(arg.arg)
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            for gen in node.generators:
                if isinstance(gen.target, ast.Name):
                    defined.add(gen.target.id)
                elif isinstance(gen.target, (ast.Tuple, ast.List)):
                    for elt in gen.target.elts:
                        if isinstance(elt, ast.Name):
                            defined.add(elt.id)
        elif isinstance(node, ast.For):
            if isinstance(node.target, ast.Name):
                defined.add(node.target.id)
            elif isinstance(node.target, (ast.Tuple, ast.List)):
                for elt in node.target.elts:
                    if isinstance(elt, ast.Name):
                        defined.add(elt.id)
        elif isinstance(node, ast.With):
            for item in node.items:
                if isinstance(item.optional_vars, ast.Name):
                    defined.add(item.optional_vars.id)
                elif isinstance(item.optional_vars, ast.Tuple):
                    for elt in item.optional_vars.elts:
                        if isinstance(elt, ast.Name):
                            defined.add(elt.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            defined.add(node.name)
    return defined


# ── File checking ────────────────────────────────────────────────

_BUILTIN_NAMES = set(dir(builtins)) | {"__name__", "__doc__", "__file__", "__annotations__", "self", "cls"}

# Modules whose imports affect parser behavior or are type-only — can't be detected as "used" by AST
_IGNORE_UNUSED = {"__future__", "typing"}


def check_file(filepath: Path) -> dict:
    result: dict = {"file": str(filepath), "missing_imports": [], "unused_imports": [], "errors": []}

    try:
        tree = ast.parse(filepath.read_text())
    except SyntaxError as e:
        result["errors"].append(f"Syntax error: {e}")
        return result
    except Exception as e:
        result["errors"].append(f"Cannot read file: {e}")
        return result

    imports = _get_imports(tree)
    names = _get_names(tree)
    defined = _get_defined_names(tree)

    missing = names - imports - _BUILTIN_NAMES - defined
    if missing:
        result["missing_imports"] = sorted(missing)

    if imports:
        used_names = names - defined
        unused = (imports - _IGNORE_UNUSED) - (imports & used_names)
        if unused:
            result["unused_imports"] = sorted(unused)

    return result


# ── Formatting ───────────────────────────────────────────────────

def _format_markdown(results: dict) -> str:
    s = results["summary"]
    output = [
        "# Python Import Check Report\n",
        f"**Path**: {results['path']}\n",
        f"**Files Checked**: {results['files_checked']}\n",
    ]

    if s["total_missing_imports"] > 0 or s["total_unused_imports"] > 0:
        output.append("\n## ⚠️ Issues Found\n")
    else:
        output.append("\n## ✅ No Issues Found\n")

    if s["total_missing_imports"] > 0:
        output.append(
            f"\n### Missing Imports\n**{s['files_with_missing']} file(s) with {s['total_missing_imports']} missing import(s)**\n"
        )
        for issue in results["issues"]:
            if issue["type"] == "missing_import":
                output.append(
                    f"- **{issue['file']}**: {', '.join(f'`{imp}`' for imp in issue['imports'])}"
                )

    if s["total_unused_imports"] > 0:
        output.append(
            f"\n### Unused Imports\n**{s['files_with_unused']} file(s) with {s['total_unused_imports']} unused import(s)**\n"
        )
        for issue in results["issues"]:
            if issue["type"] == "unused_import":
                output.append(
                    f"- **{issue['file']}**: {', '.join(f'`{imp}`' for imp in issue['imports'])}"
                )

    for issue in results["issues"]:
        if issue["type"] == "error":
            output.append(f"\n### Errors in {issue['file']}\n")
            for error in issue["details"]:
                output.append(f"- {error}")

    output.append("\n## 💡 Recommendations\n")
    if s["total_missing_imports"] > 0:
        output.append("- Add missing imports to prevent NameError at runtime")
    if s["total_unused_imports"] > 0:
        output.append("- Remove unused imports to clean up code; keep type-hint imports")

    return "\n".join(output)


# ── Execution ────────────────────────────────────────────────────

def run(
    path: str, check_missing: bool = True, check_unused: bool = True,
    output_format: str = "markdown",
    _ctx: ToolContext | None = None,
) -> str:
    agent = _ctx.agent if _ctx else None
    tool_call_id = _ctx.tool_call_id if _ctx else None
    target_path = Path(path)
    if not target_path.exists():
        return f"ERROR: Path not found: {path}"

    files = [target_path] if target_path.is_file() else list(target_path.glob("*.py"))
    files = [f for f in files if f.name not in ("__init__.py", "pycheck.py")]
    files = [f for f in files if not ("@dataclass" in f.read_text() and "class Args" in f.read_text())]

    results: dict = {
        "path": str(target_path),
        "files_checked": len(files),
        "issues": [],
        "summary": {
            "files_with_missing": 0,
            "files_with_unused": 0,
            "total_missing_imports": 0,
            "total_unused_imports": 0,
        },
    }

    for pyfile in sorted(files):
        file_result = check_file(pyfile)
        if file_result["errors"]:
            results["issues"].append({"file": pyfile.name, "type": "error", "details": file_result["errors"]})
        elif check_missing and file_result["missing_imports"]:
            results["issues"].append({
                "file": pyfile.name,
                "type": "missing_import",
                "imports": file_result["missing_imports"],
            })
            results["summary"]["files_with_missing"] += 1
            results["summary"]["total_missing_imports"] += len(file_result["missing_imports"])
        if check_unused and file_result["unused_imports"]:
            results["issues"].append({
                "file": pyfile.name,
                "type": "unused_import",
                "imports": file_result["unused_imports"],
            })
            results["summary"]["files_with_unused"] += 1
            results["summary"]["total_unused_imports"] += len(file_result["unused_imports"])

    if output_format == "json":
        return json.dumps(results, indent=2)
    return _format_markdown(results)
