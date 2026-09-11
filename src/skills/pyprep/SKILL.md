---
category: python
description: "Python project analysis — pyscan, pygraph, pyanalyze, pycheck for code structure and quality (also load: debug, refactor, code-review-workflow, testing, bug_investigation, code-simplifier, data_processing, dependency_management, graphify, performance)"
keywords: python project analysis, AST parsing, call graph, unused code detection, import checking, code quality
name: pyprep
---

# Pyprep — Python Project Preparation

## When
"python prep" | "project prep" | "codebase analysis" | "project kickoff" | "understand project" | "understand python project" | "analyze python code" | "python codebase" | "project structure" | "explore python" | "python overview" | "python analysis" | "code review" | "review code"

## Quick Start
```bash
python3 skills/pyprep/pyprep_run.py .                    # Full prep on current dir
python3 skills/pyprep/pyprep_run.py ./src --scan-only    # Scan only (no graph)
python3 skills/pyprep/pyprep_run.py ./lib --compact      # Compact output
python3 skills/pyprep/analyze.py <path>                   # Quick AST stats (files, funcs, classes, __init__ gaps)
```

## The Pyprep Sequence

### Step 1: info
- Agent context, git branch, model config
- Token usage, execution context
- Working directory, PID

### Step 2: pyscan(compact=True)
- Per-file structure: classes, functions, imports, LOC
- Use `compact=True` for projects > 50 files
- Use `max_files=20` for very large projects
- **Always run first** — gives per-file detail pygraph cannot provide

### Step 3: pygraph
- Cross-file relationships: callers, callees, impact
- Query types: summary, callers, callees, path, impact, god
- `query_type="callers"` — who calls this symbol
- `query_type="callees"` — who does this symbol call
- `query_type="impact"` — what breaks if this changes (transitive callers)
- `query_type="god"` — top-N most-called symbols
- `query_type="summary"` — graph overview
- Follow up with `grep` — pygraph misses dynamic dispatch, string refs, callbacks

### Step 4: pyanalyze
- Unused functions and imports
- Use `verify_findings=True` for grep verification
- Cannot detect callbacks or thread targets — verify with grep

### Step 5: pycheck
- Missing imports causing NameError
- Unused imports
- Cannot detect dynamic names or type-hint-only imports

## Anti-Patterns
- `bash grep -r` instead of `grep` | `bash find` instead of `glob` | Skipping pyscan → guessing | bash for file reads → use `file_read` | Multiple large tools same turn → split

## Helper
```bash
python3 skills/pyprep/pyprep_run.py .           # Full prep
python3 skills/pyprep/pyprep_run.py ./src --scan-only  # Scan only
python3 skills/pyprep/analyze.py <path>         # Quick AST stats
```

## Related Skills
- `ast-grep` — structural search
- `bug_investigation` — systematic debugging
- `code-review-workflow` — full review pipeline
- `code-simplifier` — reduce complexity
- `data_processing` — structured data
- `debug` — trace crashes
- `dependency_management` — packages
- `graphify` — knowledge graphs
- `performance` — profile
- `project-onboard` — new project
- `python_best_practices` — ruff, black, mypy
- `refactor` — restructure
- `review` — detailed review
- `security-audit` — scan secrets
- `testing` — pytest
- `tauskillmaintenance` — skill quality audit
