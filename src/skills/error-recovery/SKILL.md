---
name: error-recovery
description: Handle tool errors, API failures, session recovery, context overflow. Error handling, crash recovery, failure, retry, recover from crash, session recovery (also load: bug_investigation, tau_audit, background)
category: resilience
keywords: error, recovery, crash, failure, retry, API failure, context overflow, session, handle
---

# Error Recovery

## When
"tool error", "API failure", "session crashed", "context full", "recover session", "handle errors", "recover from crash", "retry failed"

## Error Types
| Type | Pattern | Recovery |
|------|---------|----------|
| Tool error | `TOOL_ERROR` | Retry with corrected params |
| API failure | `Connection refused` | Wait, retry with backoff |
| Context overflow | `TOOL_BLOCKED` | Compress, delegate, clear |
| Session crash | Missing output | Restart from last checkpoint |

## Recovery Patterns
- **Tool error**: Check params, retry with correction
- **API failure**: Exponential backoff (1s, 2s, 4s, 8s)
- **Context overflow**: `context_management` — fork/subagent delegation
- **Session crash**: Check audit log for last state, resume

## Checklist
- [ ] Error type identified
- [ ] Root cause determined
- [ ] Recovery strategy selected
- [ ] Retry with correction
- [ ] Verify recovery success

## Helpers

```bash
python3 skills/error-recovery/error_helper.py  # Automated error analysis
source skills/error-recovery/error_helper.sh    # bg_status, bg_cleanup
```
## Related Skills
- `bug_investigation` — systematic error analysis
- `tau_audit` — analyze error patterns in logs
- `context_management` — handle context overflow
- `background` — recover background sessions

- `info` — Agent status and diagnostics