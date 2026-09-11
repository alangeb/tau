---
category: workflow
description: "Delegate tasks to subagents — fork with full memory, spawn isolated workers, split work, run in parallel (also load: context_management, background, orchestrate, prompt-crafting, tauskillmaintenance)"
keywords: delegation, subagent, fork, task delegation, worker spawn, parallel work, task splitting, isolated workers, work distribution
name: delegation
---

# Delegation

## When
"delegate" | "subagent" | "fork" | "spawn" | "parallel tasks" | "split work" | "delegation strategy" | "delegate task" | "background task" | "run in background"

## Strategy

### subagent — Blank Slate, Cheapest
```python
subagent(task="Complete task description with all context needed")
```
- Knows ONLY task content. SYNCHRONOUS. No context copy.
- Use: well-defined tasks, code review, analysis, testing, file edits

### fork — Full Memory, Expensive
```python
fork(task="Complete task description")
```
- Inherits entire conversation. SYNCHRONOUS. Context copy.
- Use: task needs your knowledge

### background — Async, Zero Context Cost
```python
background_run(command="long-running command", timeout=600)
background_new(command="python script.py")
background_wait(session_name="...", max_seconds=600, idle_seconds=15, keywords="success|error|done")
```
- Separate tmux session. Asynchronous.
- Use: long-running independent work

## Rules
1. DELEGATE AGGRESSIVELY — never hoard context
2. Default: `subagent` (cheapest)
3. `fork` only when task needs your knowledge
4. `background` for long-running independent work
5. Give subagents COMPLETE instructions — know nothing
6. Monitor context — delegate at 30%+ (see `context_management`)

## Helpers
```bash
python3 skills/delegation/delegation.py "<description>"  # Analyze delegation strategy
python3 skills/delegation/decision.py "<description>"    # Recommend: subagent|fork|background
```

## Related Skills
- `background` — tmux session management
- `context_management` — context overflow prevention, output size control
- `info` — check context usage
- `orchestrate` — goal-driven delegation
- `performance` — performance optimization
- `prompt-crafting` — effective delegation prompts
- `task` — task framework, lifecycle, verification
- `tauskillmaintenance` — skill quality maintenance
