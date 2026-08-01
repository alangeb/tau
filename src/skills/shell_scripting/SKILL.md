---
name: shell_scripting
description: "Tau bash patterns — audit log processing, test output parsing, worktree operations. Shell script, awk, sed, grep, find (also load: background, file-ops, reference, search-replace, agent-browser, command_template, performance)"
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

# Error count
grep -c 'TOOL_ERROR\|TOOL_BLOCKED' <audit_file>
```

## Test Output Parsing
```bash
find $HOME/tau/test/output -name "status.json" | xargs grep '"status"' | sort | uniq -c
grep -oP 'duration_s=\K[\d.]+' <audit_file> | sort -n | tail -10
```

## Worktree Operations
```bash
test -f .git
MAIN_REPO=$(cat .git | sed 's/^gitdir: \(.*\)\/.git\/worktrees\/.*$/\1/')
BRANCH=$(git branch --show-current)
```

## Helper
```bash
source skills/shell_scripting/common_patterns.sh
```

## Related Skills
- `background` — tmux session management
- `file-ops` — file operations
- `reference` — Tau quick reference
- `search-replace` — find and replace patterns
- `agent-browser` — browser automation via shell
- `command_template` — shell-based commands
- `performance` — profile bottlenecks and optimize
