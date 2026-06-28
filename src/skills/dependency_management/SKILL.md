---
name: dependency_management
description: Tau dependency management — venv setup, pip installs, package isolation. Dependencies, pip, virtualenv, requirements.txt, pip install, requirements, packages (also load: python_best_practices, project-onboard)
category: development
keywords: dependency, pip, venv, virtualenv, requirements, install, package, isolation
---

# Dependency Management

## When
"install package", "pip install", "venv setup", "requirements", "missing import", "virtualenv", "packages"

## Tau Project Setup
```bash
cd $HOME/tau
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Install Tools (Tau-Specific)
```bash
pip install ruff black mypy graphifyy  # Tau dev tools
pip install --upgrade <package>        # Update single
```

## Rules
- NEVER global pip install — use venv
- `pip check` after install — verify conflicts
- `pip list --outdated` — audit regularly

## Helper

```bash
python3 skills/dependency_management/deps_check.py  # dependency_management helper
```
## Related Skills
- `python_best_practices` — linting/formatting installed tools
- `project-onboard` — discover project dependencies
- `tau_testsuite` — test dependencies

- `security-audit` — Security checks