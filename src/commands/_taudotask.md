---
description: Tau do task — execute task from 2_inprogress/
---

# /_taudotask

## Purpose
Execute a task from `tasks/2_inprogress/`. This command is invoked by `dream.py` or `automate.sh` during the task lifecycle.

## Task Lifecycle Context

```
1_todo/ → 2_inprogress/ → [/_taudotask executes] → 3_done/ or 3_failed/
```

See `skill('task')` for complete framework documentation.

## Execution Protocol

/pyprep
---
Use your ast-grep and code-simplifier skills.

**ANALYSIS LIMIT: Maximum 3 analysis tool calls (info, pyscan, pyanalyze, think). After 3 calls, you MUST start implementing.**

Look into folder structure ../tasks, you'll see the folders 1_todo, 2_inprogress, 3_done, 3_failed.
The task file in 2_inprogress describes the task/goal/activity you should perform.
Read it and implement.

**MANDATORY: After reading the task file, immediately start implementing. Do NOT create elaborate plans. Do NOT analyze further. Implement directly.**

Be careful not to miss edge cases. Goal is to perform the task/goal/activity from file you read.

Use your plan tool to create tasks to improve/fix the one most important thing. Do not change functionality. Assume everything is done for a purpose. But do make it more clean.

Then execute on all the changes. Implement the changes.

Heavily rely on subagent and fork: Do only what you must yourself, delegate the rest to fork or subagent.

$*
---
/gitcrit
---
Review your changes. Fix what needs fixing. Stay close to original instructions.
---
/gitcrit
---
Review your changes. Fix what needs fixing. Stay close to original instructions.
---
Run pytests, sanity tests. Fix code if it is broken.
Report on what was done.

## Post-Execution
After successful implementation:
1. Move task file from `2_inprogress/` to `3_done/`
2. If failed, move to `3_failed/`

## Related Skills
- `skill('task')` — Complete task framework, verification, state management
- `skill('dream')` — Dream orchestrator that invokes this command
- `skill('task_creation')` — Creating tasks for execution
