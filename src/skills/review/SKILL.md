---
description: "Detailed code review and quality assessment, inspect and analyze — pyscan pre-scan, catalog elements (also load: code-review-workflow, graphify, python_best_practices, refactor, project-onboard, pyprep)"
keywords: pyscan pre-scan, element cataloging, correctness assessment, improvement priority ranking, quality score generation
name: review
category: development
---

# Code Review

## When
"code review" | "review code quality" | "assess code" | "evaluate code" | "deep review" | "review code" | "python analysis"

## Rules
- `file_read` full files — always
- STRICT sequence — exact order, never skip/merge/reorder

## Process
### 0. Pre-Analysis
- `pyscan(path=".")` — structural inventory
- `pyanalyze(path=".")` — unused functions/imports

### 1. Read Files
- `file_read` ALL files — entire content

### 2. Inventory
- Catalog EVERY element: functions, classes, methods, variables, constants, types, imports

### 3. Element Analysis
- One-line per item — what it does
- Assess: correctness, clarity, conciseness, documentation, location, usage
- Evaluate: inline? remove?
- Use pyanalyze output for unused code candidates

### 4. Improvement Plan
- Priority: critical/high/medium/low
- Specific changes with code examples
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
- Focus on code quality, not style preferences

## Helper
```bash
python3 skills/review/review_helper.py
```

## Related Skills
- `ast-grep` — complex search/rewrite
- `code-review-workflow` — complete automated pipeline
- `code-simplifier` — code clarity improvements
- `git` — commit reviewed changes
- `git-verify` — verify code changes
- `gitcrit` — git commit critique
- `project-onboard` — understand new project
- `python_best_practices` — linting/formatting
- `pyprep` — Python project preparation
- `refactor` — restructure code
- `spec` — code review after implementation
