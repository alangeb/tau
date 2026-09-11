---
category: development
description: "Background tmux sessions — run long tasks async with wait, keyword detection, output capture (also load: shell_scripting, tmux_monitoring, dream, orchestrate, debug, delegation, test-suite-monitor, tau_testsuite, docker, health)"
keywords: tmux session management, async task execution, background process, output capture, keyword detection
name: background
---

# background

## When
"background tasks" "tmux sessions" "parallel execution" "long-running process" "background task" "run in background" "run async" "parallel task" "tmux" "terminal" "session"

## Quick Start
```python
background_run(command="pip install pkg")                        # run + wait + return
background_run(command="make", timeout=600, keywords="ok|err")   # keyword-triggered
```

## Tool Selection
- `background_run` — PREFERRED; run, wait, return output
- `background_wait` — monitor existing session; idle/keyword detection
- `background_new` + `background_exec` — interactive sessions only
- `background_capture` — read scrollback
- `background_send_keys` — interactive input (no auto-C-m)
- `background_ls` / `background_kill` — session mgmt

## background_wait Rules
- **ALWAYS multiple keywords**: `success|error|FAILED|Traceback|Exception`
- **High max_seconds** (600-1800), **low idle_seconds** (15-30)
- Single keyword dangerous — unexpected output missed

## Key Encodings
ESC: `\033` | Enter: `C-m` | Ctrl+X: `C-x`
Vim save+quit: `\033:wq\r` | nano: `C-o C-m C-x`

## Gotchas
- Independent cwd — use absolute paths or explicit `cd`
- Don't chain `&&` — separate calls
- Auto names: `tmux-agent-` prefix
- `send_keys` = interactive (no C-m), `exec` = execute (adds C-m)
- **Module caching:** changes require agent restart
- **History limit:** 5000 lines/session

## Helper
```bash
source skills/background/session_helpers.sh  # bg_status, bg_cleanup
```

## Related Skills
- `context_management` — fork/subagent/background choice
- `delegation` — task delegation patterns
- `tmux_monitoring` — polling best practices
- `tau_testsuite` — background test execution
- `docker` — container management
- `shell_scripting` — bash patterns for background tasks
- `error-recovery` — recover background sessions
- `prompt-crafting` — write background task prompts with keywords
- `debug` — interactive debugging, trace crashes, breakpoints
- `swe_bench` — SWE-bench workflow
- `tauskillmaintenance` — periodic skill audit
- `test-suite-monitor` — test suite monitoring
- `freecad` — run FreeCAD in background
- `health` — run health checks in background
- `signal-cli` — run signal daemon in background
