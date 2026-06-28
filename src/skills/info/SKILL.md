---
name: info
description: Agent status and diagnostics — working directory, PID, model config, context usage, token stats, execution mode. Agent info, context usage, token count, nesting level, model config (also load: context_management, tau_audit, error-recovery)
category: diagnostics
keywords: agent info, status, context usage, token usage, execution context, system info
---

# Info Tool

## When
"agent status", "context usage", "token count", "working directory", "nesting level", "execution mode", "model config"

## What It Returns
- Working directory (cwd)
- PID and parent PID
- Model configuration (name, API base, context limit)
- Context usage (bytes, tokens, percentage)
- Execution context (nesting level, fork/subagent mode)

## Common Use Cases
1. Check context capacity before large operations
2. Verify nesting level in deep fork chains
3. Confirm working directory after cd
4. Debug execution mode (main vs fork vs subagent)

## Context Capacity
- 200K token limit
- >80% usage — consider compression or delegation
- >90% usage — critical, delegate immediately

## Helper
```bash
python3 skills/info/info_status.py  # Quick status check (sessions + context)
```

## Related Skills
- `context_management` — manage context capacity
- `tau_audit` — analyze session logs
- `error-recovery` — handle context overflow