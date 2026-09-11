---
name: python_best_practices
description: "Python best practices — run ruff lint and auto-fix, black format, mypy type checking (also load: code-review-workflow, pyprep, refactor, review)"
category: python
keywords: ruff check auto-fix, black format enforcement, mypy type validation, import sorting, line length compliance
---

# Python Best Practices

## When
"python linting" | "code formatting" | "ruff black" | "type check" | "fix style" | "format code" | "python lint" | "code style" | "python analysis" | "code review" | "review code"

## Sequence
1. `ruff check --fix <file.py>` — auto-fix basic issues
2. `ruff check <file.py>` — check remaining
3. Fix type issues manually, re-check
4. `black <file.py>` — format
5. `mypy <file.py>` — type checking (optional, expensive)
6. Fix type issues, re-check

## Tau Lint Config
- ruff: line-length=120, target-version=py310
- black: line-length=120
- mypy: strict, ignore-missing-imports
- Run: ruff check --fix → ruff check → black → mypy (optional)

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
- `dependency_management` — manage Python dependencies
