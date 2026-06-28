---
name: task
description: Task framework — lifecycle, verification, state management. Task files, dream execution, idea-to-task pipeline, status verification (also load: dream, idea, task_creation, _taudoc)
category: orchestration
keywords: task, tasks, task framework, task lifecycle, task status, task verification, task state, dream task, idea, idea capture, task queue, task done, task failed, task inprogress, task todo, automate, automation, task file, task completion, task review, task check, verify task, is task done, task progress
---

# Task Framework

## When
"task status", "verify task", "is task done", "task framework", "task lifecycle", "task file", "dream task", "task done", "task failed", "task inprogress", "task todo", "task progress"

**Task files = PLANNING DOCUMENTS, not status reports.** File content NEVER changes after creation. LOCATION = state.

## Directory Structure
```
tasks/
├── 1_todo/           # Waiting
├── 2_inprogress/     # Active
├── 3_done/           # Complete (agent verified)
└── 3_failed/         # Failed (human intervention needed)
```

## Lifecycle
```
1_todo/ → 2_inprogress/ → agent works → 3_done/ (success)
                                    → 3_failed/ (failure)
```

## Verify Task Status (CRITICAL: By CONTENT, not filename)
```bash
ls tasks/3_done/TASK_*.md          # Likely complete
ls tasks/3_failed/TASK_*.md        # Failed
cat tasks/3_done/TASK_02.md | grep "def \|class "  # Get function names
grep -r "function_name" src/       # Search by content
grep -r "def test_" src/tests/     # Verify tests
cd src && python3 -m pytest tests/test_file.py -v  # Run tests
```

## Task File Format
```markdown
---
id: "short-descriptive-id"
title: "Concise title"
priority: "high|medium|low"
created: "YYYY-MM"
---
# Task: [Title]
## What: [Problem or improvement]
## Target: [Component/file/system]
## Approach: [How to implement]
## Success Criteria: [Definition of done]
## Testing: [How to verify]
```

## Idea → Task Pipeline
```
Idea (subconscious/ideas/) → Task (tasks/1_todo/) → Implementation → Done
```
1. `skill('idea')` → save to `subconscious/ideas/`
2. `skill('task_creation')` → save to `tasks/1_todo/`
3. `dream.py` or `automate.sh` executes
4. Agent moves file to `3_done/` or `3_failed/`

## Automation
```bash
bash tasks/automate.sh              # Process all pending tasks
python3 dream.py                    # Full self-improvement loop
python3 dream.py --n 3              # Limited cycles
```
See `skill('dream')` for details.

## Common Mistakes
1. **Filename mismatch** — Search by function name, not filename
2. **Task file = status** — Check LOCATION for status, CONTENT for plan
3. **Missing tests** — Search test function names across all test files
4. **Ignoring 3_done/** — File in `3_done/` = agent judged complete; verify with content search

## Related Skills
- `dream` — Orchestrator, cycle steps, self-improvement loop
- `idea` — Idea capture before formalizing as tasks
- `task_creation` — Creating new tasks
- `_taudoc` — Documentation structure

## Commands
- `/_taudotask` — Execute task from `2_inprogress/`
- `/_taurearch` — Re-architecture step in dream cycle
- `/_tautestcommands` — Test commands step
- `/_tautestsanity` — Sanity tests step
- `/_tauskillmaintenance` — Skill maintenance step
- `/_taudoc` — Documentation sync step
- `/_taulogreview` — Log review step

## Helper
```bash
python3 skills/task/task_verify.py                    # List all tasks
python3 skills/task/task_verify.py tasks/3_done/TASK_01.md  # Verify implementation
```
