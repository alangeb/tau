---
name: python_debugging
description: "Debug Python — background sessions, breakpoints, trace execution, interactive pdb (also load: bug_investigation, background)"
category: development
keywords: python, debug, trace, pdb, breakpoint, traceback, error, crash, interactive
---

# Python Debugging

## When
"debug python", "interactive debugging", "breakpoint", "pdb session", "trace execution", "traceback", "error in python", "debug script"

## Basic Debug Session
```python
session_name = background_new(command="bash")
background_exec(session_name=session_name, command="cd $HOME/tau/src", wait=True)
background_exec(session_name=session_name, command="python3 -i script.py", wait=False)
background_send_keys(session_name=session_name, text="breakpoint()\n")
background_send_keys(session_name=session_name, text="result = function(data)\n")
background_capture(session_name=session_name, scrollback=50)
background_kill(session_name=session_name)
```

## Common Patterns

### Lost Return Values
```python
python3 -c "import inspect; from module import func; print(inspect.signature(func))"
grep -n 'func(' code.py | grep -v 'def func'
grep -B1 -A1 'result = func(' code.py
```

### Thread Target Detection
```bash
grep -n 'threading.Thread(target=' *.py
grep -n 'target=function_name' *.py
```

### Callback Detection
```bash
grep -n '= function_name' *.py | grep -v 'def'
grep -n 'on_.*=' *.py
```

## Key Files
| Task | Command |
|------|---------|
| View execution log | `cat ~/.local/tau/log/*.audit` |
| Check errors | `grep "TOOL_ERROR" ~/.local/tau/log/*.audit` |
| View context usage | `grep "ASSISTANT" ~/.local/tau/log/*.audit` |

## Checklist
`background_new()` → `cd` to correct dir → Set up Python path → Run with `breakpoint()` or `pdb` → Inspect interactively → `background_capture()` → `background_kill()`

## Helper
```bash
python3 skills/python_debugging/debug_session.py  # python_debugging helper
```

## Related Skills
- `background` — tmux session management
- `bug_investigation` — systematic bug investigation workflow
