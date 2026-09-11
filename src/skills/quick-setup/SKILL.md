---
category: workflow
description: "Quick project setup and init — clone repository, create virtualenv, install dependencies, first commit (also load: dependency_management, git, shell_scripting, project-onboard)"
keywords: quick setup, project initialization, clone repository, virtualenv creation, dependency installation, first commit, environment verification
name: quick-setup
---

# Quick Setup

## When
"setup project", "quick start", "clone and setup", "new environment", "install dependencies", "first commit", "project initialization"

## Tau Setup
```bash
cd $HOME/tau
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install ruff black mypy graphifyy
cd src && python3 -c "import tau"
```

## Checklist
- [ ] `python3 -c "import tau"` succeeds
- [ ] `bash sanity.sh` runs
- [ ] `tau.py "hello"` responds

## Helper
```bash
python3 skills/quick-setup/setup.py <url> [branch]  # Clone + setup
```

## Related Skills
- `dependency_management` — venv and pip details
- `git` — commit and push
- `shell_scripting` — bash patterns
- `project-onboard` — understand project after setup
- `tauskillmaintenance` — skill quality maintenance
