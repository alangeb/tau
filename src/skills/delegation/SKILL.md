---
name: delegation
description: "Delegate work to subagents — subagent (isolated), fork (full memory), background (async). Delegation strategy, parallel work, task isolation, spawn child agent (also load: context_management, background, task_creation, info, performance)"
category: workflow
keywords: delegate, subagent, fork, spawn, parallel, async, background, delegation strategy, task splitting
---

# Delegation

## When
"delegate", "subagent", "fork", "spawn", "parallel tasks", "split work", "delegation strategy"

## Choose Strategy
| Situation | Use | Why |
|-----------|-----|-----|
| Well-defined task, no context needed | `subagent` | Cheapest, isolated |
| Task needs your knowledge | `fork` | Inherits context |
| Long-running, independent work | `background` | Async, no context cost |
| Code review, analysis, testing | `subagent` | Self-contained |
| File edits, refactoring | `subagent` | Give file paths + instructions |

## subagent — Blank Slate
```python
subagent(task="Complete task description with all context needed")
```
- Knows ONLY what you tell it
- SYNCHRONOUS — blocks until complete
- Best for: isolated, well-defined tasks
- Cheapest (no context copy)

## fork — Full Memory
```python
fork(task="Complete task description")
```
- Inherits entire conversation history
- SYNCHRONOUS — blocks until complete
- Best for: tasks needing your knowledge
- Expensive (context copy)

## background — Async
```python
background_run(command="long-running command", timeout=600)
# OR
background_new(command="python script.py")
background_wait(session_name="...", max_seconds=600, idle_seconds=15, keywords="success|error|done")
```
- Separate tmux session
- Asynchronous — doesn't block
- Best for: long-running, independent work
- Zero context cost

## Rules
1. **DELEGATE AGGRESSIVELY** — never hoard context
2. Default to `subagent` (cheapest)
3. Use `fork` only when task needs your knowledge
4. Use `background` for long-running independent work
5. Give subagents COMPLETE instructions (they know nothing)
6. Monitor context — delegate at 30%+ usage
7. At 50%+ — AGGRESSIVELY delegate
8. At 70%+ — STOP non-critical tool calls, delegate immediately

## Anti-Patterns
- Reading entire large files without limits
- Running multiple large analysis tools in same turn
- Doing work yourself that could be delegated
- Ignoring context usage percentage
- Waiting for compression to kick in

## Related Skills
- `background` — tmux session management
- `context_management` — context overflow prevention
- `info` — check context usage
- `task_creation` — create tasks for delegation
- `performance` — optimize token usage
