---
name: python_best_practices
description: Python linting, formatting, type checking — ruff, black, mypy sequence. Python lint, code style, formatting, type hints, fix style, format code (also load: code-review-workflow, review, git, code-simplifier)
category: python
keywords: python, lint, format, style, ruff, black, mypy, type hints, code quality
---

# Python Best Practices

## When
"python linting", "code formatting", "ruff black", "type check", "fix style", "format code", "python lint", "code style"

## Sequence
1. `ruff check --fix <file.py>` — auto-fix basic issues
2. `ruff check <file.py>` — check remaining
3. Fix type issues manually, re-check until resolved
4. `black <file.py>` — format

## Helper
```bash
python3 skills/python_best_practices/lint_helper.py <path>  # Run full lint+format sequence
```

## Optional (when requested — expensive)
5. `mypy <file.py>` — type checking
6. Fix type issues, re-check until resolved

## Install (if missing)
- `pip install ruff`
- `pip install black`
- `pip install mypy`

## Related Skills
- `code-review-workflow` — complete review pipeline
- `review` — detailed code review process
- `code-simplifier` — code clarity improvements
- `dependency_management` — Tau dependency management
- `project-onboard` — Understand new project
- `git-verify` — Verify code changes
- `git` — Git worktree operations