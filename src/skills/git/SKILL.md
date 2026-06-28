---
name: git
description: Git worktree operations — commit, sync with master, verify diffs. Git operations, branch management, commit, push, pull (also load: code-review-workflow, review, python_best_practices, git-advanced, security-audit)
category: development
keywords: git worktree, commit, sync, rebase, merge, branch management, push, pull, fast-forward
---

# Git Worktree Operations

## When
"git commit", "git sync", "merge master", "rebase worktree", "git worktree", "sync with master", "commit changes"

## Facts
| Key | Value |
|-----|-------|
| Worktree | `$(pwd)` |
| Branch | `$(git branch --show-current)` — NOT folder name |
| Main repo | `$(cat .git \| sed 's/^gitdir: \(.*\)\/.git\/worktrees\/.*$/\1/')` |

## Never
- Switch branches — worktree LOCKED to one branch
- Use folder name as branch name — always `git branch --show-current`
- Remove worktree
- Use `git merge` for sync — use `git rebase` + `git merge --ff-only`
- Blindly accept `--theirs` or `--ours` — examine both
- Force-push or reset master — master is sacred

## Verify Changes
```bash
git -C . diff --stat HEAD
git -C . diff HEAD
git -C . diff HEAD -- <file>  # Specific
```

### Checklist
- [ ] Changes match intent
- [ ] No unintended modifications
- [ ] Formatting consistent
- [ ] No leftover debug code

## Commit Changes
1. Verify worktree: `test -f .git` (FILE, not directory)
2. Verify branch: `git branch --show-current`
3. `git status` — if clean, report and STOP
4. `git diff` — review (use checklist)
5. `git add -A`
6. `git commit` — specific message
7. `git log --oneline -3` — verify
8. Report

## Sync Worktree with Master

### 1. Verify identity
```
test -f .git
MAIN_REPO=$(cat .git | sed 's/^gitdir: \(.*\)\/.git\/worktrees\/.*$/\1/')
test -d "$MAIN_REPO/.git"
BRANCH=$(git branch --show-current)
```

### 2. Rebase worktree onto master
```
git fetch "$MAIN_REPO" master
git rebase FETCH_HEAD "$BRANCH"
# Conflicts: examine --ours (master) and --theirs (worktree), resolve intelligently
# Cannot resolve: STOP
```

### 3. Fast-forward merge into master
```
ORIG_DIR=$(pwd)
cd "$MAIN_REPO"
git checkout master
git merge --ff-only "$BRANCH"
# --ff-only fails: STOP
```

### 4. Reset worktree to master
```
cd "$ORIG_DIR"
git reset --hard FETCH_HEAD
```

### 5. Verify sync
```
git rev-parse HEAD == $(cd "$MAIN_REPO" && git rev-parse master)
```

## Report
- **ERROR:** rebase failed, --ff-only failed, identity check failed
- **WARNING:** sync verification failed
- Include full diagnostic context

## Helper
```bash
python3 skills/git/git_worktree_sync.py   # Verify worktree + main repo
python3 skills/git/git_worktree_sync.py sync  # Full sync with master
source skills/git/worktree_ops.sh
```

## Related Skills
- `swe_bench` — SWE-bench workflow
- `code-review-workflow` — full review pipeline
- `python_best_practices` — linting/formatting
- `review` — detailed code review
- `git-advanced` — bisect, cherry-pick, history analysis
- `security-audit` — check for leaked secrets in commits
