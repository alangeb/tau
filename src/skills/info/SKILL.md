---
category: diagnostics
description: "Check agent info and status, context usage, token count — monitor context window, model config, execution mode (also load: context_management, health, orchestrate, tau_audit)"
keywords: agent status, context usage, token count, model config, execution context, agent diagnostics, info check, context window
name: info
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
See AGENT.md — CONTEXT MANAGEMENT section for thresholds.

## Helper
```bash
python3 skills/info/info_status.py  # Quick status check (sessions + context)
```

## Related Skills
- `context_management` — manage context capacity
- `error-recovery` — handle context overflow
- `tau_audit` — analyze session logs
- `performance` — profile bottlenecks and optimize
- `delegation` — check context usage before delegating
- `project-onboard` — initial project diagnostics
