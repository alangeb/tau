---
name: git-advanced
description: "Advanced git — bisect, cherry-pick, revert, log analysis, history, stash, blame, reflog (also load: bug_investigation, git, tau_audit, code-review-workflow, git-verify)"
category: development
keywords: git, bisect, cherry-pick, revert, log, history, blame, stash, advanced
---

# Git Advanced

## When
"git log analysis", "git bisect", "git stash", "cherry-pick", "git revert", "git blame", "git history", "bisect", "cherry-pick"

## Tau Worktree Bisect
```bash
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
git cherry-pick <commit>
git cherry-pick <start>..<end>    # Range
git cherry-pick --abort           # Conflict
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
- `bug_investigation` — use bisect for bug hunting
- `git` — basic worktree operations
- `tau_audit` — analyze commit patterns
- `code-review-workflow` — review changes before committing
- `git-verify` — verify code changes
