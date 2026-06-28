#!/usr/bin/env python3
"""git_worktree_sync.py — Worktree sync helper."""
import subprocess, sys, os

def verify_worktree():
    """Verify current directory is a worktree."""
    if not os.path.isfile('.git'):
        print("ERROR: Not a worktree")
        return False
    result = subprocess.run(["git", "branch", "--show-current"],
                          capture_output=True, text=True)
    branch = result.stdout.strip()
    if not branch:
        print("ERROR: No branch detected")
        return False
    print(f"Branch: {branch}")
    return True

def get_main_repo():
    """Extract main repo path from worktree .git file."""
    with open('.git') as f:
        for line in f:
            if line.startswith('gitdir:'):
                path = line.split('worktrees/')[0].strip()
                return path.rstrip('/')
    return None

def sync_with_master():
    """Sync worktree with master (rebase + ff-only merge)."""
    if not verify_worktree():
        return False
    main_repo = get_main_repo()
    if not main_repo:
        print("ERROR: Could not find main repo")
        return False
    branch = subprocess.run(["git", "branch", "--show-current"],
                          capture_output=True, text=True).stdout.strip()
    # Fetch master
    subprocess.run(["git", "fetch", main_repo, "master"], check=True)
    # Rebase worktree onto master
    result = subprocess.run(["git", "rebase", "FETCH_HEAD", branch])
    if result.returncode != 0:
        print("ERROR: Rebase failed")
        return False
    # Fast-forward merge into master
    os.chdir(main_repo)
    subprocess.run(["git", "checkout", "master"], check=True)
    result = subprocess.run(["git", "merge", "--ff-only", branch])
    if result.returncode != 0:
        print("ERROR: --ff-only failed")
        return False
    # Reset worktree to master
    os.chdir(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True).stdout.strip())
    subprocess.run(["git", "reset", "--hard", "FETCH_HEAD"], check=True)
    print("Sync complete")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "sync":
        sync_with_master()
    else:
        verify_worktree()
        main_repo = get_main_repo()
        if main_repo:
            print(f"Main repo: {main_repo}")
