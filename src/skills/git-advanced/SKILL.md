---
name: git-advanced
description: Advanced git — bisect, cherry-pick, revert, log analysis, history. Git bisect, git log, git history, git stash, cherry-pick, revert, blame (also load: git, bug_investigation, tau_audit)
category: development
keywords: git, bisect, cherry-pick, revert, log, history, blame, stash, advanced
---

# Git Advanced

## When
"git log analysis", "git bisect", "git stash", "cherry-pick", "git revert", "git blame", "git history", "bisect", "cherry-pick"

## Tau Worktree Bisect
```bash
# Bisect in worktree (NEVER switch branches)
git bisect start
git bisect bad
git bisect good <commit>
# Resolve in worktree, NEVER --theirs/--ours blindly
git bisect reset
```

## Log Analysis
```bash
git log --oneline -20
git log --stat --since="1 week ago"
git log --author="name" --oneline
git log -S"search_string" --oneline
```

## Cherry-Pick (Tau-Specific)
```bash
# Cherry-pick into worktree
git cherry-pick <commit>
# Range
git cherry-pick <start>..<end>
# Abort if conflict
git cherry-pick --abort
```

## Rules
- NEVER merge `tau-bot-tool-development` into master — different architecture
- ALWAYS cherry-pick selectively with sanity-sh verification
- Worktree LOCKED to one branch — NEVER switch

## Helper

```bash
python3 skills/git-advanced/git_ops.py  # git advanced helper
```
## Related Skills
- `git` — basic worktree operations
- `code-review-workflow` — review changes before committing
- `bug_investigation` — use bisect for bug hunting
- `tau_audit` — analyze commit patterns
