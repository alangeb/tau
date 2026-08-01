---
name: info
description: "Agent status and diagnostics — working directory, PID, model config, context usage, token stats. System info (also load: context_management, error-recovery, tau_audit, performance)"
category: diagnostics
keywords: agent info, status, context usage, token usage, execution context, system info
---

# Info Tool

## When
"agent status", "context usage", "token count", "working directory", "nesting level", "execution mode", "model config"

## Returns
- Working directory (cwd), PID, parent PID
- Model config (name, API base, context limit)
- Context usage (bytes, tokens, percentage)
- Execution context (nesting level, fork/subagent mode)

## Context Capacity
- 200K token limit
- >80% — compress or delegate
- >90% — critical, delegate immediately

## Helper
```bash
python3 skills/info/info_status.py  # Quick status check (sessions + context)
```

## Related Skills
- `context_management` — manage context capacity
- `error-recovery` — handle context overflow
- `tau_audit` — analyze session logs
- `performance` — profile bottlenecks and optimize
