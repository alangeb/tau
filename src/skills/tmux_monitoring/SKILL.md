---
name: tmux_monitoring
description: Monitor tmux sessions — polling intervals, completion detection, anti-patterns. Tmux, session monitoring, terminal multiplexer, monitor sessions, terminal (also load: background)
category: development
keywords: tmux, monitor, session, polling, background, terminal, completion, detect
---

# Tmux Monitoring

## When
"monitor tmux", "poll background", "check session status", "background monitoring", "session polling", "monitor sessions", "terminal"

## Timing
| Task Duration | Poll Interval |
|--------------|---------------|
| < 5s | 30s |
| 5-60s | 60-120s |
| 60-300s | 120-180s |
| > 300s | 300s+ |

**Default**: `sleep 120` for most background tasks.

## Pattern
```bash
background_new(command="your_command")
# Initial check
background_tail {"session_name": "...", "lines": 10}
# Poll loop
while session_active; do
    sleep 120
    background_tail {"session_name": "...", "lines": 10}
done
```

## Completion Detection
- Session not found: "can't find pane" error
- Output shows "Test Suite Completed!" or similar
- Status files updated in output directories

## Anti-Pattern
```bash
# WRONG — too frequent, creates entropy warnings
while true; do
    background_tail {"session_name": "...", "lines": 10}
    sleep 5
done
```

## Helper

```bash
source skills/tmux_monitoring/monitor_helpers.sh
```
## Related Skills
- `background` — tmux session management
- `test-suite-monitor` — complete test monitoring workflow
