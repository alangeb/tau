#!/usr/bin/env python3
"""Quick project setup — clone, venv, deps, first commit."""
import subprocess, sys, os

def run(cmd, cwd=None):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if r.stdout: print(r.stdout[:500])
    if r.returncode != 0 and r.stderr: print(r.stderr[:200], file=sys.stderr)
    return r.returncode == 0

def setup(url, branch=None):
    # Clone
    name = url.rstrip('/').split('/')[-1].replace('.git', '')
    if not os.path.exists(name):
        if not run(f"git clone {'-b ' + branch if branch else ''}{url}"):
            return False
    
    # Setup
    os.chdir(name)
    run("python3 -m venv .venv")
    run("source .venv/bin/activate")
    if os.path.exists('requirements.txt'):
        run("pip install -r requirements.txt")
    run("pip install ruff black mypy")
    
    # First commit
    run("git add -A")
    run('git commit -m "initial: project setup"')
    run("git log --oneline -1")
    return True

if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else None
    branch = sys.argv[2] if len(sys.argv) > 2 else None
    if not url:
        print("Usage: setup.py <repo-url> [branch]")
        sys.exit(1)
    setup(url, branch)
