---
name: task_creation
description: "Create tasks for dream execution — .md files in tasks/1_todo/. Queue task, schedule improvement, defer work (also load: task, dream, idea, skill_template)"
category: orchestration
keywords: task creation, create task, new task, queue task, schedule improvement, defer work, dream task, add task, task file, task format, task queue
---

# Task Creation

## When
"create task", "new task", "queue task", "schedule improvement", "defer work", "dream task", "add task"

## What
Tasks are `.md` files in `tasks/1_todo/`. Dream.py picks them up via `/_taudotask`.

## Tau May Create Tasks
**Tau is AUTHORIZED to create tasks on its own.** Deficiency, bug, missing feature, or improvement opportunity → create task immediately. Do NOT wait for permission.

## Task File Format
```markdown
---
id: "short-descriptive-id"
title: "Concise title"
priority: "high|medium|low"
created: "YYYY-MM"
---

# Task: [Title]
## What: [Problem or improvement needed]
## Target: [Component/file/system affected]
## Approach: [How to implement, if known]
## Success Criteria: [Definition of done]
## Testing: [How to verify]
```

## Naming
- **Recommended**: `TASK_##.md` format (e.g., `TASK_01.md`) — processed in numerical order
- Alternative: lowercase-with-dashes (e.g., `my-feature.md`) — sorts alphabetically
- Place in `tasks/1_todo/`
- One task per file, concise
- Enough detail for `/_taudotask` to execute without clarification

## Task Ordering (CRITICAL)
Tasks processed in **filename-sorted order** (lexicographic):
- `TASK_##.md` files: `TASK_01.md` → `TASK_02.md` → `TASK_03.md`
- Non-TASK files sort alphabetically relative to `TASK_` files
- Use `tasks/queue.sh "description"` to auto-generate numbered files
- Manual files: use `TASK_##.md` format to control order

## Privacy
- NO personal info, real timestamps, user names, email addresses
- Use `$HOME` instead of `/home/alangeb`

## Quick Create
```bash
bash tasks/queue.sh "Brief description of the task"
```
Auto-generates numbered file in `1_todo/`.

## Helper
```bash
python3 skills/task_creation/task_create.py <title> [high|medium|low]
```

## Related Skills
- `dream` — Orchestrator that consumes these tasks
- `idea` — Capture ideas before formalizing as tasks
- `task` — Complete task framework, verification, state management
- `skill_template` — Skill creation format
