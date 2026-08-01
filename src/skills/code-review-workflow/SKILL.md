---
name: code-review-workflow
description: Complete code review pipeline — pyscan, pyanalyze, pygraph, pycheck, ruff, black, summary (also load: ast-grep, code-simplifier, context_management, documentation, file-ops, git-advanced, graphify, python_best_practices, review, bug_investigation, git-verify, performance)
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
pygraph(path=".")                          # Cross-file call graphs
pycheck(path=".")                          # Missing imports check
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
## Call Graph: [pygraph findings]
## Import Issues: [pycheck findings]
## Linting: [ruff findings]
## Formatting: [black applied]
## Summary: [issues found, severity, recommendations]
```

## Helper
```bash
python3 skills/code-review-workflow/review_pipeline.py <path>  # Full pipeline
```

## Related Skills
- `ast-grep` — complex search/rewrite
- `code-simplifier` — code clarity improvements
- `python_best_practices` — linting/formatting sequence
- `review` — detailed manual review process
- `bug_investigation` — systematic bug analysis
- `git-verify` — verify code changes
- `performance` — profile bottlenecks
