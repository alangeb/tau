---
description: Python project preparation — run info, pyscan, pygraph, pyanalyze, pycheck on the target
---

# /pyprep — Python Project Preparation

Run the following tools to understand the project structure:

1. Run `info` to get agent and project information
2. Run `pyscan` on `$1` (or `./` if not specified) to analyze project structure
3. Run `pygraph` on `$1` (or `./` if not specified) to build call graphs and relationships
4. Run `pyanalyze` on `$1` (or `./` if not specified) to check for unused code
5. Run `pycheck` on `$1` (or `./` if not specified) to check for missing imports

Be thorough in your analysis. Use the results to understand the codebase before making changes.

**Why each tool:**
- `info` — Agent context, git branch, model config, token usage
- `pyscan` — Per-file structure: classes, functions, imports, LOC
- `pygraph` — Cross-file relationships: callers, callees, impact analysis, god classes
- `pyanalyze` — Unused functions and imports
- `pycheck` — Missing imports causing NameError at runtime
