---
name: python_best_practices
description: "Python linting, code formatting, type checking — ruff, black, mypy sequence (also load: code-review-workflow, review, git, code-simplifier, file-ops, shell_scripting)"
category: python
keywords: python, lint, format, style, ruff, black, mypy, type hints, code quality
---

# Python Best Practices

## When
"python linting", "code formatting", "ruff black", "type check", "fix style", "format code", "python lint", "code style"

## Sequence
1. `ruff check --fix <file.py>` — auto-fix basic issues
2. `ruff check <file.py>` — check remaining
3. Fix type issues manually, re-check
4. `black <file.py>` — format

## Optional (expensive)
5. `mypy <file.py>` — type checking
6. Fix type issues, re-check

## Install (if missing)
- `pip install ruff black mypy`

## Helper
```bash
python3 skills/python_best_practices/lint_helper.py <path>  # Run full lint+format sequence
```

## Related Skills
- `code-review-workflow` — complete review pipeline
- `code-simplifier` — code clarity improvements
- `file-ops` — file read/edit patterns
- `git` — Git worktree operations
- `review` — detailed code review process
- `shell_scripting` — shell patterns
