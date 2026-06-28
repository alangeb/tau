---
name: task_creation
description: Create tasks for dream execution — .md files in tasks/1_todo/, self-initiated improvements. Create task, new task, queue task, schedule improvement, defer work, dream task, add task (also load: task, dream, idea, skill_template)
category: orchestration
keywords: task creation, create task, new task, queue task, schedule improvement, defer work, dream task, add task, task file, task format, task queue
---

# Task Creation

## When
"create task", "new task", "queue task", "schedule improvement", "defer work", "dream task", "add task"

## What
Tasks are `.md` files in `tasks/1_todo/`. Dream.py picks them up via `/_taudotask`.

## Tau May Create Tasks
**Tau is AUTHORIZED to create tasks on its own.** When Tau encounters a deficiency, bug, missing feature, or improvement opportunity, create task immediately. Do NOT wait for permission.

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
- Lowercase-with-dashes: `my-feature.md`
- Place in `tasks/1_todo/`
- One task per file, concise
- Enough detail for `/_taudotask` to execute without clarification

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

## Task Lifecycle Overview

```
Idea (subconscious/ideas/) → Task (tasks/1_todo/) → 2_inprogress/ → 3_done/ or 3_failed/
```

1. Capture idea: `skill('idea')`
2. Create task: this skill
3. Dream executes: `skill('dream')`
4. Verify status: `skill('task')`

## Related Skills
- `task` — Complete task framework, verification, state management
- `dream` — Orchestrator that consumes these tasks
- `idea` — Capture ideas before formalizing as tasks
- `skill_template` — Format for creating skills