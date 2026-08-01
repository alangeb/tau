---
name: tmux_monitoring
description: "Monitor tmux sessions — polling intervals, completion detection, anti-patterns (also load: background, test-suite-monitor, tau_testsuite)"
category: development
keywords: tmux, monitor, session, polling, background, terminal, completion, detect
---

# Tmux Monitoring

## When
"monitor tmux", "poll background", "check session status", "background monitoring", "session polling", "monitor sessions", "terminal"

## Preferred: background_wait
ALWAYS use `background_wait` over `bash sleep N`. Detects hangs, catches errors, returns results.

```python
background_wait(
    session_name="tmux-agent-xxx",
    max_seconds=1800,       # Hard timeout
    idle_seconds=30,        # Return if no output for 30s
    keywords="error|warning|complete|done|FAILED|SUCCESS|PASSED|Traceback|Exception",
    tail_lines=30
)
```

**Multiple keywords MANDATORY** — single keyword misses unexpected output.

## Timing Guide
| Task Duration | idle_seconds | max_seconds |
|--------------|-------------|-------------|
| < 5s | 15 | 60 |
| 5-60s | 15 | 120 |
| 60-300s | 30 | 600 |
| > 300s | 30 | 1800 |

## Pattern
```python
background_new(command="your_command")
background_wait(session_name="...", max_seconds=600, idle_seconds=30, keywords="error|done|complete")
background_capture(session_name="...", lines=30)
```

## Completion Detection
- Keyword match, idle timeout, hard timeout, or session death
- "can't find pane" = session ended
- "Test Suite Completed!" = check keywords

## Anti-Patterns
```python
# WRONG — raw sleep, no detection
bash("sleep 180")
background_capture(session_name="...", lines=10)

# WRONG — too frequent polling
while session_active:
    background_capture(session_name="...", lines=10)
    bash("sleep 5")

# WRONG — single keyword
background_wait(session_name="...", keywords="complete")  # Misses errors!
```

## Helper
```bash
source skills/tmux_monitoring/monitor_helpers.sh
```

## Related Skills
- `background` — tmux session management
- `test-suite-monitor` — complete test monitoring workflow
- `tau_testsuite` — test structure and helpers
