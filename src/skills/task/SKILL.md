---
category: orchestration
description: "Create and track todo tasks with structured workflow — task framework for project management (also load: manifest, orchestrate, dream, spec, _taudoc, idea, plan_template, prompt-crafting)"
keywords: task creation, task verification, task tracking, structured workflow, task status, task dependency
name: task
---

# Task Framework
## When
"task status" | "verify task" | "is task done" | "task framework" | "task lifecycle" | "task file" | "dream task" | "task done" | "task failed" | "task inprogress" | "task todo" | "task progress" | "task list" | "create task" | "new task" | "queue task" | "schedule improvement" | "defer work"

**Task files = PLANNING DOCUMENTS.** Content NEVER changes. LOCATION = state. Tau AUTHORIZED to create tasks. Deficiency, bug, missing feature, improvement → create immediately. No wait.

## Directory Structure
```
tasks/
├── 1_todo/           # Waiting
├── 2_inprogress/     # Active
├── 3_done/           # Complete (agent verified)
└── 3_failed/         # Failed (human intervention needed)
```

## Ordering & Naming
`1_todo/` processed in **filename-sorted order**.
- **Recommended**: `TASK_##.md` (e.g., `TASK_01.md`)
- One task per file; enough detail for `/_taudotask` to execute
- Use `bash tasks/queue.sh "description"` to auto-generate numbered files

## Privacy
NO personal info, real timestamps, user names, email addresses. Use `$HOME` instead of `/home/user`.

## Task File Format
Frontmatter: `id`, `title`, `priority` (high|medium|low), `created` (YYYY-MM). Body: `## What`, `## Target`, `## Approach`, `## Success Criteria`, `## Testing`.

## Verify Task Status
```bash
ls tasks/3_done/TASK_*.md          # Complete
ls tasks/3_failed/TASK_*.md        # Failed
cd src && python3 -m pytest tests/test_file.py -v  # Run tests
```

## Helpers
```bash
bash tasks/automate.sh              # Process all pending tasks
python3 dream.py                    # Full self-improvement loop
python3 skills/task/task_verify.py                    # List all tasks
python3 skills/task/task_verify.py tasks/3_done/TASK_01.md  # Verify implementation
python3 skills/task/task_create.py <title> [high|medium|low]  # Create task
```

## Related Skills
- `manifest` — hierarchical plan tracking, goal management
- `delegation` — Delegate tasks to subagents
- `dream` — Self-improvement orchestrator loop
- `idea` — Idea capture, source of tasks
- `manifest` — Delegation manifests
- `orchestrate` — Goal-driven delegation
- `plan_template` — Task planning templates
- `spec` — Spec-driven tasks
- `sum` — State summarization