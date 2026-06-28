---
name: project-onboard
description: Understand new project — info, pyscan, pyanalyze, plan, initial reads. New project, explore codebase, project overview, kickoff, what is this codebase (also load: code-review-workflow, review)
category: development
keywords: project, onboard, new project, explore, codebase, overview, kickoff, understand
---

# Project Onboard

## When
"understand project", "new project", "what is this codebase", "project overview", "explore codebase"

## Sequence
```bash
info
pyscan(path=".")
pyanalyze(path=".")
plan(action="create")
file_read(path="README.md")
file_read(path="CLAUDE.md")
```

## Output
```
=== PROJECT OVERVIEW ===
## Location: [cwd]
## Scale: [N files, N LOC, N classes, N functions]
## Quality: [unused code, issues]
## Structure: [key modules, dependencies]
## Standards: [coding conventions, tools]
```

## Helper

```bash
python3 skills/project-onboard/onboard.py  # project onboard helper
```
## Related Skills
- `code-review-workflow` — deeper analysis
- `review` — detailed review process
- `python_best_practices` — linting/formatting
- `dependency_management` — discover project dependencies
- `readme_template` — document project structure
- `idea` — Capture ideas for features