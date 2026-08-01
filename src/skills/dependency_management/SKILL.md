---
name: dependency_management
description: "Tau dependency management — venv setup, pip installs, package isolation, requirements (also load: project-onboard, python_best_practices, graphify, security-audit, tau_testsuite)"
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
- `project-onboard` — discover project dependencies
- `python_best_practices` — linting/formatting installed tools
- `graphify` — knowledge graph analysis
- `security-audit` — Security checks
- `tau_testsuite` — test dependencies
