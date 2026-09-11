---
category: security
description: "Security audit — scan secrets, API keys, credentials, file permissions, vulnerability check, Python deps (also load: grep_tool, git-verify, shell_scripting, dependency_management, pyprep, reference)"
keywords: security audit, hardcoded secrets, API keys, leaked credentials, file permissions, gitignore rules, credential scan, security scan, dependency audit, pip freeze, requirements check, version conflict, outdated package, dependency tree, pip check
name: security-audit
---

# Security Audit

## When
"security check" "dependency audit" "secrets scan" "sensitive files" "vulnerability check" "audit" "health check" "check dependencies" "pip freeze" "version conflict" "outdated package"

## Checks

### API Keys
```bash
grep -rn "password\|secret\|api_key\|token" . --include="*.py"
grep -rn "AKIA[0-9A-Z]{16}" .          # AWS keys
grep -rn "ghp_[a-zA-Z0-9]{36}" .       # GitHub tokens
```

### Sensitive Files
```bash
find . -name "*.pem" -o -name "*.key" -o -name "*.crt"
find . -name ".env" -o -name "*.env.*"
find . -name "*.pgpass" -o -name ".netrc"
```

### Audit Log Privacy
```bash
grep -rn "api_key\|password\|secret" ~/.local/tau/log/
```

### Dependencies
```bash
pip check              # Check conflicts
pip list --outdated    # Find outdated packages
pip freeze > req.txt   # Export current deps
pip install -r req.txt # Install from file
pipdeptree             # Show dependency tree
pip audit              # Security audit (if available)
```

#### Tau Dependencies
Key packages: `pyyaml`, `requests`, `graphviz` (optional)
- Check `requirements.txt` for pinned versions
- Verify no conflicts: `pip check`

## Checklist
- [ ] No hardcoded secrets
- [ ] Sensitive files in .gitignore
- [ ] No credentials in commit history
- [ ] Permissions correct (600 for sensitive)
- [ ] Audit logs sanitized
- [ ] `pip check` passes (no conflicts)
- [ ] No outdated critical packages
- [ ] `requirements.txt` matches `pip freeze`
- [ ] No duplicate packages

## Helpers
```bash
python3 skills/security-audit/scan.py        # Security scan
python3 skills/security-audit/audit_deps.py   # Dependency audit
```

## Related Skills
- `bug_investigation` — investigate security issues
- `code-review-workflow` — review code for security issues
- `dependency_management` — manage Python dependencies
- `git` — check commit history for leaked secrets
- `grep_tool` — pattern search for credentials
- `shell_scripting` — shell-based scanning
- `pyprep` — project analysis
- `reference` — quick reference for tau commands
- `tauskillmaintenance` — skill quality audit
