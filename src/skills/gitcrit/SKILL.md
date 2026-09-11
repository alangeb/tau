---
description: "critique commit messages, check commit quality, review git history, analyze change scope, verify message format and conventions (also load: code-review-workflow, git, git-advanced, git-verify)"
keywords: git critique, commit message review, commit quality, git history review, commit standards, git message critique, commit best practices
name: gitcrit
category: git
---

# GitCrit — Commit Critique

## When
"critique commits" "git review" "commit quality" "git history review" "commit message check" "git" "commit" "code review" "review code"

## Helper
```bash
python3 skills/gitcrit/git_critique.py analyze       # Analyze recent commits
python3 skills/gitcrit/git_critique.py messages      # Check message quality
python3 skills/gitcrit/git_critique.py scope         # Check change scope
```

## Phase 1: Code Review
- Run `pyanalyze` + `pyscan` on changed files
- Use `code-simplifier` for complexity, `review` for quality, `ast-grep` for patterns
- Focus on git diff, last changes
- Critique root cause, not symptoms

### Commit Message Quality
| Criteria | Good | Bad |
|----------|------|-----|
| Length | 50 char subject | Too long/short |
| Format | "type: description" | "fix stuff" |
| Body | Explains why | Only what |
| Scope | One change | Multiple changes |

Types: feat, fix, refactor, docs, style, test, chore, perf, ci

## Phase 2: Issue Review
- Derive new list, focus root cause
- Symptoms → find root cause
- Summary of findings

## Phase 3: Cross-Reference Audit

### Stale Reference Check — for every file deleted/renamed:
1. `grep -rn` across codebase
2. Check docs (README.md, TAU.md, designs/)
3. Check skills (skills/*/SKILL.md "also load")
4. Check commands (commands/*.md)
5. Check tests (tests/*.py)
6. Check config (tau.json)

### Documentation Drift
- User-facing changes → update TAU.md
- Skill changes → update "also load" refs
- Command changes → update README.md
- Report ALL stale refs with file:line + fix

## Related Skills
- `git` — basic git operations
- `git-advanced` — advanced git workflows
- `code-review-workflow` — code review process
- `review` — code quality review
- `git-verify` — verify git state
- `code-simplifier` — complexity analysis
- `ast-grep` — pattern matching
