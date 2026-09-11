---
name: code-review-workflow
description: "Review code quality, audit codebase — pyscan, pyanalyze, pygraph, ruff, black, pycheck pipeline for automated code review (also load: ast-grep, python_best_practices, review, code-simplifier, git-verify, gitcrit, refactor, pyprep)"
category: development
keywords: pyscan structural inventory, pyanalyze usage check, pygraph call graph traversal, ruff linting, black formatting, static quality check
---

# code-review-workflow

## When
"review code" "check quality" "audit codebase" "code health check" "code review" "python analysis"

## Pipeline
```bash
python3 skills/code-review-workflow/review_pipeline.py <path>  # Full pipeline
```

## Manual Sequence
```bash
pyscan(path=".")           # Structural inventory
pyanalyze(path=".")        # Usage analysis, unused code
pygraph(path=".")          # Cross-file call graphs
pycheck(path=".")          # Missing imports
ruff check --fix <file>    # Auto-fix linting
ruff check <file>          # Verify
black <file>               # Format
# mypy <file>              # Type check (expensive, optional)
```

## Helper
```bash
python3 skills/code-review-workflow/review_pipeline.py <path>  # Full pipeline
```

## Related Skills
- `ast-grep` — structural search/rewrite
- `code-simplifier` — code clarity improvements
- `python_best_practices` — linting/formatting sequence
- `review` — detailed manual review
- `git-verify` — verify code changes
- `security-audit` — security review
- `gitcrit` — git commit critique
- `debug` — debug issues found during review
- `documentation` — docstring and changelog patterns
- `git-advanced` — bisect, cherry-pick, history analysis
- `testing` — Write pytest tests
- `graphify` — visualize code structure
- `pyprep` — Python project preparation
- `file-ops` — file operations during review
- `git` — git operations during review
- `performance` — performance review
- `plan_template` — planning review
- `project-onboard` — onboarding review
- `search-replace` — search/replace during review
- `pyprep` — Python project analysis
- `refactor` — code restructuring
- `tauskillmaintenance` — skill quality maintenance
