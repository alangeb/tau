---
description: "git operations, commit, push, rebase, branch management, worktree sync, verify branch, review diff, add and stage changes (also load: git-advanced, git-verify, gitcrit, quick-setup, release_management)"
keywords: git commit, git push, git rebase, branch management, worktree sync, git operations, version control, git workflow
name: git
category: git
---

# Git Worktree Operations

## When
"git commit" "git sync" "merge master" "rebase worktree" "git worktree" "sync with master" "commit changes" "git" "commit" "version control"

## Facts
| Key | Value |
|-----|-------|
| Worktree | `$(pwd)` |
| Branch | `$(git branch --show-current)` — NOT folder name |
| Main repo | `$(cat .git \| sed 's/^gitdir: \(.*\)\/.git\/worktrees\/.*$/\1/')` |

## Never
- Switch branches — worktree LOCKED to one branch
- Use folder name as branch — always `git branch --show-current`
- Remove worktree
- Use `git merge` for sync — use `git rebase` + `git merge --ff-only`
- Blindly accept `--theirs`/`--ours` — examine both
- Force-push or reset master — master is sacred

## Commit Changes
1. `test -f .git` (FILE, not directory)
2. `git branch --show-current` — verify branch
3. `git status` — clean? report and STOP
4. `git diff` — review
5. `git add -A`
6. `git commit` — specific message
7. `git log --oneline -3` — verify

## Sync Worktree with Master
```bash
test -f .git
MAIN_REPO=$(cat .git | sed 's/^gitdir: \(.*\)\/.git\/worktrees\/.*$/\1/')
test -d "$MAIN_REPO/.git"
BRANCH=$(git branch --show-current)
git fetch "$MAIN_REPO" master
git rebase FETCH_HEAD "$BRANCH"
# Conflicts: examine --ours (master) vs --theirs (worktree), resolve intelligently; cannot resolve: STOP
cd "$MAIN_REPO" && git checkout master && git merge --ff-only "$BRANCH"
# --ff-only fails: STOP
cd "$(pwd)" && git reset --hard FETCH_HEAD
test "$(git rev-parse HEAD)" = "$(cd "$MAIN_REPO" && git rev-parse master)"
```

## Report — **ERROR:** rebase/--ff-only/identity failed | **WARNING:** sync verification failed | Include full diagnostics

## Helper
```bash
python3 skills/git/git_worktree_sync.py   # Verify worktree + main repo
python3 skills/git/git_worktree_sync.py sync  # Full sync with master
source skills/git/worktree_ops.sh
```

## Related Skills
- `code-review-workflow` — full review pipeline
- `git-advanced` — bisect, cherry-pick, history analysis
- `git-verify` — verify code changes
- `gitcrit` — Git commit critique
- `security-audit` — check for leaked secrets in commits
- `swe_bench` — patch management
- `refactor` — Code refactoring
- `file-ops` — File operations with git integration
- `python_best_practices` — Python code quality before commit
- `review` — Code review before commit
- `edit-and-run` — edit code, test, iterate
- `spec` — Commit spec + implementation
- `quick-setup` — Project initialization
- `release_management` — Version bumping, changelog, release notes
