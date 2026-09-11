---
category: development
description: "Onboard to new project and codebase — pyscan, pygraph, pyanalyze to map structure, find setup (also load: pyprep, review, quick-setup)"
keywords: new codebase exploration, pyscan structural scan, README review, dependency discovery, module hierarchy mapping
name: project-onboard
---


# Project Onboard

## When
"understand project"
"new project"
"what is this codebase"
"project overview"
"explore codebase"
"project structure"
"code review"
"python analysis"
"review code"
## Sequence
```bash
info
pyscan(path=".")
pyanalyze(path=".")
manifest_create(goal="...", title="...", subtasks="...")
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
- `code-review-workflow` — Deeper analysis
- `file-ops` — File read/edit patterns
- `info` — Agent status and diagnostics
- `review` — Detailed review process
- `shell_scripting` — Shell patterns
- `dependency_management` — discover project dependencies
- `readme_template` — README documentation
- `idea` — Capture ideas for features
- `pyprep` — Python project preparation
- `quick-setup` — Project initialization
