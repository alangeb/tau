---
category: development
description: "Shell script patterns — bash utilities, grep, file ops, process management, error handling (also load: grep_tool, file-ops, debug, error-recovery, agent-browser, background, command_template, data_processing, dependency_management, docker)"
keywords: bash scripting, shell utilities, process management, error handling, file operations, pipe chains
name: shell_scripting
---

# Shell Scripting

## When
"bash pattern" "audit log processing" "test output parsing" "shell one-liner" "bash script" "shell commands" "grep" "find" "sort" "uniq" "xargs" "pipe" "pipeline" "write a script" "shell script" "bash command" "run command" "text processing" "awk" "sed"

## Audit Log Processing
```bash
for f in ~/.local/tau/log/*_2026*_1.audit; do
  grep -oP "final_name='[^']*" "$f" | sed "s/final_name='"//
done | sort | uniq -c | sort -rn

grep -rh '"skill_name":\s*"[^"]*"' ~/.local/tau/log/*_2026*_1.audit | \
  grep -oP '"skill_name":\s*"\K[^"]+' | sort | uniq -c | sort -rn

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
python3 skills/shell_scripting/shell_script_gen.py <pattern>  # audit_count, audit_skill, audit_errors, parse_json
```

## Related Skills
- `edit-and-run` — edit, test, iterate loop
- `agent-browser` — automate browser workflows
- `background` — tmux session management
- `search-replace` — search and replace patterns, bulk edit files
- `command_template` — shell-based commands
- `data_processing` — Structured data processing
- `dependency_management` — package management
- `docker` — automate docker workflows
- `file-ops` — file operations
- `freecad` — automate build/verify pipeline
- `grep_tool` — grep search patterns
- `image` — image file operations
- `performance` — profile bottlenecks and optimize
- `project-onboard` — shell patterns for project exploration
- `python_best_practices` — lint/format sequences
- `quick-setup` — project initialization
- `reference` — Tau quick reference
- `search-replace` — find and replace patterns
- `security-audit` — credential scanning
- `signal-cli` — signal-cli automation
- `tau_audit` — tau audit skill
- `test-suite-monitor` — background test execution
- `web-research` — web scraping
