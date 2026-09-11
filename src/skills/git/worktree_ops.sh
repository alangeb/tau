#!/bin/bash
# worktree_ops.sh — Git worktree operation helpers
# Source or run: source worktree_ops.sh; wt_verify

set -e

# Verify worktree identity
wt_verify() {
    test -f .git || { echo "ERROR: Not a worktree"; return 1; }
    local branch
    branch=$(git branch --show-current)
    local main_repo
    main_repo=$(cat .git | sed 's/^gitdir: \(.*\)\/.git\/worktrees\/.*$/\1/')
    echo "Branch: $branch"
    echo "Main repo: $main_repo"
}

# Show current branch
wt_show_branch() {
    git branch --show-current
}

# Show main repo path
wt_show_main_repo() {
    test -f .git || { echo "ERROR: Not a worktree"; return 1; }
    cat .git | sed 's/^gitdir: \(.*\)\/.git\/worktrees\/.*$/\1/'
}

# Quick status check
wt_status() {
    wt_verify || return 1
    echo "--- Files ---"
    git status --short
    echo "--- Diff ---"
    git diff --stat HEAD 2>/dev/null || true
}

# Sync check: compare worktree HEAD with main repo
wt_sync_check() {
    wt_verify || return 1
    local main_repo
    main_repo=$(wt_show_main_repo)
    local wt_head main_head
    wt_head=$(git rev-parse HEAD)
    main_head=$(git -C "$main_repo" rev-parse HEAD)
    if [ "$wt_head" = "$main_head" ]; then
        echo "SYNCED: Worktree HEAD matches main repo HEAD"
    else
        echo "DIVERGED:"
        echo "  Worktree: $wt_head"
        echo "  Main:     $main_head"
    fi
}

# List worktrees
wt_list() {
    local main_repo="$1"
    [ -z "$main_repo" ] && main_repo="."
    git -C "$main_repo" worktree list
}

# Dispatch when run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-help}" in
        verify) wt_verify ;;
        show-branch) wt_show_branch ;;
        show-main-repo) wt_show_main_repo ;;
        status) wt_status ;;
        sync-check) wt_sync_check ;;
        list) wt_list "$2" ;;
        help|--help|-h)
            echo "Usage: worktree_ops.sh {verify|show-branch|show-main-repo|status|sync-check|list [repo]}"
            ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
fi
