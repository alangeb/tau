---
category: resilience
description: "Recover from crashed sessions and failed operations, retry, handle API backoff, context overflow error recovery (also load: debug, context_management, tau_audit, edit-and-run, shell_scripting)"
keywords: crashed session restore, failed operation retry, API exponential backoff, context overflow escape, exception handler patterns
name: error-recovery
---

# Error Recovery

## When
"tool error" | "API failure" | "session crashed" | "context full" | "recover session" | "handle errors" | "recover from crash" | "retry failed" | "error" | "debug" | "traceback"

## Error Types & Recovery
| Type | Pattern | Recovery |
|------|---------|----------|
| Tool error | `TOOL_ERROR` | Retry with corrected params |
| API failure | `Connection refused` | Exponential backoff (1s, 2s, 4s, 8s) |
| Context overflow | `TOOL_BLOCKED` | Delegate via fork/subagent |
| Session crash | Missing output | Check audit log, resume from checkpoint |

## Helpers
```bash
python3 skills/error-recovery/error_helper.py  # Automated error analysis
source skills/error-recovery/error_helper.sh    # bg_status, bg_cleanup
```

## Related Skills
- `edit-and-run` — edit, test, iterate loop
- `background` — recover background sessions
- `bug_investigation` — systematic error analysis
- `tau_audit` — analyze error patterns in logs
- `context_management` — handle context overflow
- `performance` — performance optimization
- `debug` — debug root cause of errors
- `info` — check agent status during recovery
