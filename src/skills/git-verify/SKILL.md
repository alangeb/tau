---
description: "git diff, review changes, confirm correctness before commit, verify modifications match intent, check formatting consistency (also load: code-review-workflow, git, git-advanced, gitcrit, security-audit)"
keywords: git diff, review changes, pre-commit review, commit verification, change review, git verify, correctness check
name: git-verify
category: git
---

# Git Verify

## When
"verify changes" "check diff" "review modifications" "confirm changes" "git diff review" "check changes" "review diff" "git" "commit" "code review" "review code"

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
- `review` — detailed code review
- `git` — basic worktree operations
- `git-advanced` — bisect, cherry-pick, history analysis
- `search-replace` — confirm modifications
- `gitcrit` — Git commit critique
- `refactor` — verify refactoring changes
- `security-audit` — security review of changes
