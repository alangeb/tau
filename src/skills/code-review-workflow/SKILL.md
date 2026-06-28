---
name: code-review-workflow
description: Complete code review pipeline — pyscan, pyanalyze, ruff, black, summary. Review code, check quality, audit codebase (also load: review, python_best_practices, ast-grep, code-simplifier)
category: code-quality
keywords: review pipeline, automated review, code quality, lint, format, type check, full review
---

# Code Review Workflow

## When
"review code", "check quality", "audit codebase", "code health check"

## Sequence
```bash
python3 skills/code-review-workflow/review_pipeline.py <path>  # Full pipeline
# Or manual:
pyscan(path=".")                          # Structural inventory
pyanalyze(path=".")                        # Usage analysis, unused code
ruff check --fix <file>                   # Auto-fix linting
ruff check <file>                          # Verify remaining issues
black <file>                                # Format
# Optional: mypy <file>                   # Type check (expensive)
```

## Output
```
=== CODE REVIEW: <file> ===
## Structural Issues: [pyscan findings]
## Usage Issues: [pyanalyze findings]
## Linting: [ruff findings]
## Formatting: [black applied]
## Summary: [issues found, severity, recommendations]
```

## Related Skills
- `review` — detailed manual review process
- `python_best_practices` — linting/formatting sequence
- `ast-grep` — complex search/rewrite
- `git` — commit changes after review
- `code-simplifier` — code clarity improvements
- `bug_investigation` — systematic bug analysis
- `graphify` — knowledge graph for architecture overview
- `context_management` — delegate review
- `documentation` — docstring patterns
- `file-ops` — file operations
- `git-advanced` — advanced git operations
- `git-verify` — git verification
- `performance` — performance analysis
- `plan_template` — plan structure
- `project-onboard` — project context
- `python_debugging` — debugging
- `search-replace` — search and replace
- `security-audit` — security analysis
