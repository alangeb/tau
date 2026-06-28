---
name: background
description: Run commands in background — tmux sessions, parallel tasks, long-running processes, monitor output, wait for completion. Background tasks, parallel execution, async, concurrent (also load: tmux_monitoring, test-suite-monitor, context_management)
category: development
keywords: tmux, background process, session, async, concurrent, parallel, wait, monitor
---

# background

## When
"background tasks", "tmux sessions", "monitor processes", "run in background", "parallel execution"

## Tools
| Tool | Purpose |
|------|---------|
| `background_new` | Create session (default: bash) |
| `background_ls` | List active agent sessions |
| `background_kill` | Kill session or all agent sessions |
| `background_exec` | Execute command in session |
| `background_capture` | Capture pane output with scrollback |
| `background_tail` | Show last N lines from output |
| `background_send_keys` | Send keystrokes without execution |
| `background_wait` | **Wait with idle/keyword detection (PREFERRED over `bash sleep`)** |

## `background_wait` — Smart Waiting
**Use INSTEAD of `bash sleep N`.** Auto-detects: hung (idle), expected output (keywords), timeout.

### Parameters
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `session_name` | Yes | — | tmux session (must start with `tmux-agent-`) |
| `max_seconds` | Yes | — | Maximum wait seconds |
| `idle_seconds` | Yes | — | Return if no output this long |
| `keywords` | No | (empty) | Regex to match — **ALWAYS use multiple keywords** (e.g. `"error\|warning\|complete\|done"`) |
| `tail_lines` | No | 30 | Output lines returned |
| `poll_interval` | No | 1 | Seconds between checks |

### ⚠️ Keyword Safety
NEVER use single keyword. Process outputs unexpected word → missed → wait until timeout. Always cover success, failure, AND error patterns.

### Examples
```python
background_wait(session_name="tmux-agent-build", max_seconds=300, idle_seconds=30, keywords="error|warning|complete|done")
background_wait(session_name="tmux-agent-tests", max_seconds=1800, idle_seconds=60, keywords="FAILED|PASSED|ERROR|Traceback|Exception")
```

### Return Values
- `KEYWORD MATCH:` — keywords found
- `IDLE:` — no output for `idle_seconds`, likely hung
- `TIMEOUT:` — max time reached
- `SESSION DEAD:` — session disappeared

## Key Encodings
| Key | Syntax |
|-----|--------|
| ESC | `\033` |
| Enter | `C-m` |
| Ctrl+X | `C-x` |

**Common:** vim save+quit: `\033:wq\r` | nano: `C-o C-m C-x` | Cancel: `C-c`

## Gotchas
- Independent working dirs — use absolute paths or explicit `cd`
- Don't chain `&&` — use separate calls
- Auto-generated names: `tmux-agent-` prefix
- `send_keys` = interactive (no C-m), `exec` = execute (adds C-m)
- `scrollback >= 30` for useful history

## Helpers
```bash
source skills/background/session_helpers.sh  # bg_status, bg_cleanup
```

## Related Skills
- `tmux_monitoring` — polling best practices
- `test-suite-monitor` — test monitoring workflow
- `context_management` — fork/subagent/background choice
- `shell_scripting` — commands for background
- `python_debugging` — interactive debug sessions
- `tau_testsuite` — background test execution
- `signal-cli` — daemon management
- `docker` — container management
- `error-recovery` — error handling
- `freecad` — CAD modeling
- `swe_bench` — benchmark workflow