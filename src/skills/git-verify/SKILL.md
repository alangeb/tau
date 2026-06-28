---
name: git-verify
description: Verify code changes — git diff, review modifications, confirm correctness. Git diff, verify changes, review diff, check changes (also load: code-review-workflow, review)
category: development
keywords: git, diff, verify, changes, review, modifications, confirm, check
---

# Git Verify

## When
"verify changes", "check diff", "review modifications", "confirm changes", "git diff review", "check changes", "review diff"

## Sequence
```bash
git -C . diff --stat HEAD
git -C . diff HEAD
git -C . diff HEAD -- <file>  # Specific
```

## Checklist
- [ ] Changes match intent
- [ ] No unintended modifications
- [ ] Formatting consistent
- [ ] No leftover debug code

## Helper

```bash
python3 skills/git-verify/verify.py  # git verify helper
```
## Related Skills
- `code-review-workflow` — full review pipeline
- `python_best_practices` — linting/formatting
- `review` — detailed code review
- `search-replace` — Find and replace patterns across files