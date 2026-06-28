---
name: review
description: Code review process — detailed analysis, inventory, improvement plan. Review code, code analysis, quality assessment (also load: code-review-workflow, python_best_practices, ast-grep, code-simplifier, git, git-verify, project-onboard)
category: code-quality
keywords: code review, code analysis, quality assessment, deep review, evaluate code, assess code
---

# Code Review

## When
"code review", "review code quality", "assess code", "evaluate code", "deep review"

## Rules
- `file_read` full files every time — even if previously read
- STRICT sequence — execute steps in exact order, never skip/merge/reorder

## Process

### 0. Pre-Analysis
- `pyscan(path=".")` — structural inventory
- `pyanalyze(path=".")` — unused functions/imports

### 1. Read Files
- `file_read` ALL files in full — entire content, not partials

### 2. Inventory
- Catalog EVERY element: functions, classes, methods, variables, constants, types, imports
- Leverage pyscan output from Step 0

### 3. Element Analysis (One at a Time)
- One-line comment per item — what it does
- Assess: correctness, clarity, conciseness, documentation, location, usage
- Evaluate: inline? remove?
- Use pyanalyze output for unused code candidates

### 4. Improvement Plan
- Priority ranking: critical/high/medium/low
- Specific actionable changes with code examples
- Trade-off analysis

## Output Format
```
=== CODE REVIEW: <filename> ===
## Pre-Analysis: [pyscan + pyanalyze results]
## Inventory: [- <type>: <name> — <brief>]
## Detailed Analysis: [### <name> → Purpose, Assessment, Recommendation]
## Improvement Plan: [### Critical/High/Medium/Low → <change> — <impact>]
## Summary: [Total items, Critical count, Rating: <score/10>]
```

## Notes
- Never modify reviewed files
- Can output to file if requested
- Focus on code quality, not style preferences

## Helper
```bash
python3 skills/review/review_helper.py  # review helper
```

## Related Skills
- `code-review-workflow` — complete automated pipeline
- `python_best_practices` — linting/formatting
- `ast-grep` — complex search/rewrite
- `code-simplifier` — code clarity improvements
- `git` — commit reviewed changes

- `project-onboard` — Understand new project
- `git-verify` — Verify code changes