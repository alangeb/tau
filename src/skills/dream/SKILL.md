---
name: dream
description: Dream orchestrator — self-improvement loop. Dream.py, task lifecycle, cycle steps, automation (also load: _taudoc, task, task_creation, tau_audit, tauskillmaintenance, idea, skill_template)
category: orchestration
keywords: dream, dream.py, dream cycle, dream task, dream orchestrator, self-improvement, automation, automate, task lifecycle, task queue, task execution, task framework, task status, task verification, idea, idea capture, task done, task failed
---

# Dream

## When
"dream", "dream.py", "self-improvement loop", "dream cycle", "task orchestrator", "dream tasks", "automation", "automate", "task framework", "task lifecycle"

## What
`dream.py` — orchestrator for Tau self-improvement. Handles deterministic ops (file ops, git, testing, timeout, logging). Invokes `tau.py` only for LLM-driven work.

## CRITICAL RULE
**Tau must NEVER perform dream tasks directly.** Dream is ONLY invoked through `dream.py`.
**Never invoke `/_taudotask`, `/_taurearch`, `/_tautestcommands`, `/_tautestsanity`, `/_tauskillmaintenance`, `/_taudoc`, or `/_taulogreview` directly.**

## Task Lifecycle
- `tasks/1_todo/` — waiting
- `tasks/2_inprogress/` — active
- `tasks/3_done/` — completed
- `tasks/3_failed/` — failed

### Flow
1. dream.py scans `1_todo/*.md` → **sorted by filename** (lexicographic)
2. Moves to `2_inprogress/`
3. Runs `tau.py "/_taudotask"` — Tau implements
4. Runs tests (`pytest` + `sanity.sh`)
5. Success: `git commit` → `3_done/`
6. Failure: `git revert` → `3_failed/`

### Task Ordering (CRITICAL)
Tasks processed in **filename-sorted order** (`sorted(glob("1_todo/*.md"))`).
- `TASK_##.md` convention: `TASK_01.md`, `TASK_02.md` → numerical order
- Non-TASK files sort alphabetically relative to `TASK_` files
- Use `tasks/queue.sh "description"` to auto-generate numbered task files
- Manual files: use `TASK_##.md` format to control order

## Cycle Steps (8, in order)
1. **Process tasks** — `/_taudotask`
2. **Re-architecture** (x3) — `/_taurearch`
3. **Test commands** — `/_tautestcommands`
4. **Test sanity** — `/_tautestsanity`
5. **Skill maintenance** — `/_tauskillmaintenance`
6. **Doc sync** — `/_taudoc`
7. **Log review** — `/_taulogreview`
8. **Wiki maintenance** — `/_tauwiki`

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

## Helper
```bash
python3 skills/dream/task_status.py  # Show pending/active tasks
```

## Related Skills
- `_taudoc` — Documentation structure
- `task` — Complete task framework, verification, state management
- `task_creation` — Creating tasks for dream execution
- `tau_audit` — Analyze agent behavior
- `tauskillmaintenance` — Skill audit process
- `idea` — Idea capture before formalizing as tasks
- `skill_template` — Skill creation format
