---
name: security-audit
description: Security checks — API keys, config permissions, sensitive data in logs. Security, vulnerability scan, secrets, sensitive data (also load: bug_investigation, code-review-workflow, dependency_management, git)
category: security
keywords: security, vulnerability, scan, secrets, sensitive, API key, permissions, audit
---

# Security Audit

## When
"security check", "dependency audit", "secrets scan", "sensitive files", "vulnerability check"

## Tau-Specific Checks

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

## Checklist
- [ ] No hardcoded secrets
- [ ] Sensitive files in .gitignore
- [ ] No credentials in commit history
- [ ] Permissions correct (600 for sensitive)
- [ ] Audit logs sanitized

## Helper
```bash
python3 skills/security-audit/scan.py  # security audit helper
```

## Related Skills
- `bug_investigation` — investigate security issues
- `code-review-workflow` — review code for security issues
- `dependency_management` — manage Python dependencies
- `git` — check commit history for leaked secrets
