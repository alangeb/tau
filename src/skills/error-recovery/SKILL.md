---
name: error-recovery
description: "Handle tool errors, API failures, session recovery, context overflow. Crash recovery, retry with backoff (also load: background, bug_investigation, context_management, info, performance, tau_audit)"
category: resilience
keywords: error, recovery, crash, failure, retry, API failure, context overflow, session, handle
---

# Error Recovery

## When
"tool error", "API failure", "session crashed", "context full", "recover session", "handle errors", "recover from crash", "retry failed"

## Error Types & Recovery
| Type | Pattern | Recovery |
|------|---------|----------|
| Tool error | `TOOL_ERROR` | Retry with corrected params |
| API failure | `Connection refused` | Exponential backoff (1s, 2s, 4s, 8s) |
| Context overflow | `TOOL_BLOCKED` | Delegate via fork/subagent |
| Session crash | Missing output | Check audit log, resume from checkpoint |

## Checklist
- [ ] Error type identified
- [ ] Root cause determined
- [ ] Recovery applied
- [ ] Success verified

## Helpers
```bash
python3 skills/error-recovery/error_helper.py  # Automated error analysis
source skills/error-recovery/error_helper.sh    # bg_status, bg_cleanup
```

## Related Skills
- `background` — recover background sessions
- `bug_investigation` — systematic error analysis
- `tau_audit` — analyze error patterns in logs
- `context_management` — handle context overflow
- `performance` — performance optimization
