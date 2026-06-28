---
name: security-audit
description: Security checks — API keys, config permissions, sensitive data in logs. Security, vulnerability scan, secrets, sensitive data (also load: bug_investigation, code-review-workflow)
category: security
keywords: security, vulnerability, scan, secrets, sensitive, API key, permissions, audit
---

# Security Audit

## When
"security check", "dependency audit", "secrets scan", "sensitive files", "vulnerability check"

## Tau-Specific Checks

### API Key Handling
```bash
# Scan for hardcoded keys
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
# Check for sensitive data in logs
grep -rn "api_key\|password\|secret" ~/.local/tau/log/
```

## Checklist
- [ ] No hardcoded secrets in code
- [ ] Sensitive files in .gitignore
- [ ] No credentials in commit history
- [ ] File permissions correct (600 for sensitive)
- [ ] Audit logs sanitized

## Helper

```bash
python3 skills/security-audit/scan.py  # security audit helper
```
## Related Skills
- `dependency_management` — manage Python dependencies
- `bug_investigation` — investigate security issues
- `code-review-workflow` — review code for security issues
- `git` — check commit history for leaked secrets
