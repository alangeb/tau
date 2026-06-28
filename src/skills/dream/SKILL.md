---
name: dream
description: Dream orchestrator — self-improvement loop. Dream.py, task lifecycle, cycle steps, automation (also load: task, task_creation, _taudoc, tauskillmaintenance, tau_audit)
category: orchestration
keywords: dream, dream.py, dream cycle, dream task, dream orchestrator, self-improvement, automation, automate, task lifecycle, task queue, task execution, task framework, task status, task verification, idea, idea capture, task done, task failed
---

# Dream

## When
"dream", "dream.py", "self-improvement loop", "dream cycle", "task orchestrator", "dream tasks", "automation", "automate", "task framework", "task lifecycle"

## What
`dream.py` — programmatic orchestrator for Tau self-improvement. Handles deterministic ops (file ops, git, testing, timeout, logging). Invokes `tau.py` only for LLM-driven work.

## CRITICAL RULE
**Tau must NEVER perform dream tasks on its own.** Dream is ONLY invoked through `dream.py`.
**Never invoke `/_taudotask`, `/_taurearch`, `/_tautestcommands`, `/_tautestsanity`, `/_tauskillmaintenance`, `/_taudoc`, or `/_taulogreview` directly.**

## Task Lifecycle
- `tasks/1_todo/` — waiting (`.md` files)
- `tasks/2_inprogress/` — being worked on
- `tasks/3_done/` — completed
- `tasks/3_failed/` — failed

### Flow
1. dream.py scans `1_todo/*.md`
2. Moves to `2_inprogress/`
3. Runs `tau.py "/_taudotask"` — Tau implements
4. Runs tests (`pytest` + `sanity.sh`)
5. Success: `git commit` → `3_done/`
6. Failure: `git revert` → `3_failed/`

## Cycle Steps (7, in order)
1. **Process tasks** — `/_taudotask`
2. **Re-architecture** (x3) — `/_taurearch`
3. **Test commands** — `/_tautestcommands`
4. **Test sanity** — `/_tautestsanity`
5. **Skill maintenance** — `/_tauskillmaintenance`
6. **Doc sync** — `/_taudoc`
7. **Log review** — `/_taulogreview`

### Per-Step
- Run tau command → test → commit or revert
- Git clean between steps
- Timeout: 6h per step
- SIGINT = graceful, SIGTERM = force kill
- `dream.stop` file halts loop

## Invocation
```bash
python3 dream.py              # Forever (default)
python3 dream.py --n 3        # Limited cycles
python3 dream.py --llm deepseek
python3 dream.py --dry-run    # No LLM calls
```

## Related Skills
- `task` — Complete task framework, verification, state management
- `task_creation` — Creating tasks for dream execution
- `idea` — Idea capture before formalizing as tasks
- `_taudoc` — Documentation structure
- `tauskillmaintenance` — Skill audit process
- `tau_audit` — Analyze agent behavior
- `skill_template` — Skill creation format