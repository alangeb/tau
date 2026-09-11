---
category: development
description: "Debug Python errors and tracebacks — pdb, breakpoint(), interactive tmux sessions, crash reproduction (also load: bug_investigation, pyprep, ast-grep, background, edit-and-run, error-recovery, performance, tauskillmaintenance, testing, shell_scripting)"
keywords: pdb interactive session, breakpoint placement, traceback parsing, crash reproduction, post-mortem inspection, exception trace, variable inspection, frame navigation, debug python, interactive debugging, debug script
name: debug
---

# Debug

## When
"debug" | "investigate bug" | "find root cause" | "fix error" | "trace execution" | "crash" | "traceback" | "exception" | "error" | "fix bug" | "debug python" | "interactive debugging" | "breakpoint" | "pdb session" | "error in python" | "debug script"

## Tools
`pyscan(compact=True)` structure | `pygraph` callers/callees | `grep` references | `ast-grep` structural search | `tau_audit` logs | `background_exec` interactive

## Interactive Debug Session (tmux)
```python
session_name = background_new(command="bash")
background_exec(session_name=session_name, command="cd $HOME/tau/src", wait=True)
background_exec(session_name=session_name, command="python3 -i script.py", wait=False)
background_send_keys(session_name=session_name, text="breakpoint()\n")
background_send_keys(session_name=session_name, text="result = function(data)\n")
background_capture(session_name=session_name, scrollback=50)
background_kill(session_name=session_name)
```

## Key Files
| Task | Command |
|------|---------|
| View execution log | `cat ~/.local/tau/log/*.audit` |
| Check errors | `grep "TOOL_ERROR" ~/.local/tau/log/*.audit` |
| View context usage | `grep "ASSISTANT" ~/.local/tau/log/*.audit` |

## Tau-Specific Errors
| Error | Cause | Fix |
|-------|-------|-----|
| `TOOL_BLOCKED` in audit | Context overflow | Delegate via subagent |
| `Connection refused` | API down | Exponential backoff |
| `ModuleNotFoundError` for tools | Not in sys.path | `cd $HOME/tau/src` |

## Helper Scripts
```bash
python3 skills/debug/debug_trace.py <traceback.txt>   # Parse traceback
python3 skills/debug/debug_session.py       # Interactive debug session template
```

## Related Skills
- `edit-and-run` — edit, test, iterate loop
- `bug_investigation` — systematic investigation, traceback parsing, root cause
- `code-review-workflow` — verify fixes
- `error-recovery` — crash/session recovery
- `performance` — performance debugging
- `pyprep` — Python development workflow
- `tauskillmaintenance` — skill audit, debug trace helper
- `testing` — pytest tests, fixtures, coverage
- `tau_audit` — log analysis