---
name: shell_scripting
description: Tau bash patterns — audit log processing, test output parsing, worktree operations. Bash scripting, shell commands, text processing, awk, sed, grep, find, sort, uniq, xargs, pipe (also load: background, reference, search-replace, file-ops)
category: development
keywords: bash, shell, script, audit log, test output, worktree, awk, sed, grep, find, sort, uniq, xargs, pipe
---

# Shell Scripting

## When
"bash pattern", "audit log processing", "test output parsing", "shell one-liner", "find and process", "bash script", "shell commands", "grep", "find", "sort", "uniq", "xargs", "pipe", "pipeline"

## Audit Log Processing
```bash
# Tool usage across all logs
for f in ~/.local/tau/log/*_2026*_1.audit; do
  grep -oP "final_name='[^']*" "$f" | sed "s/final_name='"//
done | sort | uniq -c | sort -rn

# Skill loading frequency
grep -rh '"skill_name":\s*"[^"]*"' ~/.local/tau/log/*_2026*_1.audit | \
  grep -oP '"skill_name":\s*"\K[^"]+' | sort | uniq -c | sort -rn

# Error patterns
grep -c 'TOOL_ERROR\|TOOL_BLOCKED' <audit_file>
```

## Test Output Parsing
```bash
# Status summary
find $HOME/tau/test/output -name "status.json" | xargs grep '"status"' | sort | uniq -c

# Duration analysis
grep -oP 'duration_s=\K[\d.]+' <audit_file> | sort -n | tail -10
```

## Worktree Operations
```bash
# Verify worktree identity
test -f .git
MAIN_REPO=$(cat .git | sed 's/^gitdir: \(.*\)\/.git\/worktrees\/.*$/\1/')
BRANCH=$(git branch --show-current)
```

## Gotchas
- **Quoting**: `'single'` for literal, `"double"` for expansion
- **Pipefail**: `set -o pipefail` to catch errors in pipes
- **Globbing**: `shopt -s nullglob` to handle empty globs

## Helper

```bash
source skills/shell_scripting/common_patterns.sh
```
## Related Skills
- `image` — image loading and vision models
- `docker` — container management
- `background` — tmux session management
- `agent-browser` — browser automation via shell
- `tau_audit` — audit log analysis
- `tau_testsuite` — test output parsing
- `command_template` — shell-based commands

- `performance` — Performance
- `signal-cli` — Signal CLI and JSON-RPC API
- `freecad` — Headless FreeCAD 3D modeling
- `web-research` — Web research
- `search-replace` — Find and replace patterns across files
- `reference` — Tau quick reference
- `file-ops` — File operations