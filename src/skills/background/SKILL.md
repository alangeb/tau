---
name: background
description: Run commands in background — tmux sessions, parallel tasks, long-running processes, monitor output (also load: context_management, delegation, tau_testsuite, test-suite-monitor, tmux_monitoring, docker, error-recovery, freecad)
category: development
keywords: tmux, background process, session, async, concurrent, parallel, wait, monitor
---

# background

## When
"background tasks", "tmux sessions", "monitor processes", "run in background", "parallel execution"

## Tools
| Tool | Purpose |
|------|---------|
| `background_run` | **Run + wait + return output (PREFERRED)** |
| `background_new` | Create session (advanced) |
| `background_ls` | List active sessions |
| `background_kill` | Kill session/all agent sessions |
| `background_exec` | Execute in session (advanced) |
| `background_capture` | Capture pane scrollback |
| `background_send_keys` | Send keystrokes (no execution) |
| `background_wait` | **Wait with idle/keyword detection (advanced)** |

## `background_run` — Simple (PREFERRED)
```python
background_run(command="pip install package")
background_run(command="make build", timeout=600)
background_run(command="deploy.sh", keywords="success|error|failed")
```

### Parameters
| Param | Default | Description |
|-------|---------|-------------|
| `command` | (required) | Command to execute |
| `timeout` | 300 | Max seconds |
| `idle_seconds` | 30 | Return if no output this long |
| `keywords` | (empty) | Regex — returns immediately on match |
| `session_name` | (auto) | Session name |
| `capture_lines` | 30 | Output lines to return |

### Return Values
`COMPLETED:` prompt detected | `KEYWORD MATCH:` regex hit | `IDLE:` no output for idle_seconds | `TIMEOUT:` max time | `SESSION DEAD:` gone

## `background_wait` — Advanced Monitoring
```python
background_wait(session_name="tmux-agent-X", max_seconds=600, idle_seconds=15,
    keywords="success|error|failed|Traceback|Exception")
```
**ALWAYS use multiple keywords** covering success, failure, AND error patterns.

### Parameters
| Param | Required | Description |
|-------|----------|-------------|
| `session_name` | Yes | tmux session (`tmux-agent-` prefix) |
| `max_seconds` | Yes | Max wait |
| `idle_seconds` | Yes | Return if no output this long |
| `keywords` | No | Regex — multiple patterns mandatory |
| `tail_lines` | 30 | Output lines returned |
| `poll_interval` | 1 | Seconds between checks |

### Return Values
`KEYWORD MATCH:` | `IDLE:` | `TIMEOUT:` | `SESSION DEAD:` | `PROCESS EXITED:` prompt detected

## `background_capture`
```python
background_capture(session_name="tmux-agent-build")          # last 30 lines
background_capture(session_name="tmux-agent-build", lines=100)
```

## Key Encodings
| Key | Syntax |
|-----|--------|
| ESC | `\033` |
| Enter | `C-m` |
| Ctrl+X | `C-x` |

Vim save+quit: `\033:wq\r` | nano: `C-o C-m C-x` | Cancel: `C-c`

## Gotchas
- Independent working dirs — use absolute paths or explicit `cd`
- Don't chain `&&` — use separate calls
- Auto-generated names: `tmux-agent-` prefix
- `send_keys` = interactive (no C-m), `exec` = execute (adds C-m)
- **Module caching:** Changes require agent session restart
- **History limit:** 5000 lines per session (configurable via `_DEFAULT_HISTORY_LIMIT`)

## Helpers
```bash
source skills/background/session_helpers.sh  # bg_status, bg_cleanup
```

## Related Skills
- `context_management` — fork/subagent/background choice
- `tau_testsuite` — background test execution
- `test-suite-monitor` — test monitoring workflow
- `tmux_monitoring` — polling best practices
- `docker` — container management
- `error-recovery` — error handling
- `freecad` — CAD modeling
