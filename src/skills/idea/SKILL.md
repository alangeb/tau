---
name: idea
description: Capture ideas for features, fixes, improvements. Brainstorm, ideation, idea-to-task pipeline (also load: plan_template, project-onboard, task, task_creation, bug_investigation, dream, wiki)
category: development
keywords: idea, ideas, brainstorm, ideation, feature idea, bug fix, improvement, capture idea, thought capture, new feature, novel concept, idea pipeline, idea to task, subconscious, ideas folder
---

# Idea Capture

## When
"new feature", "bug fix", "refactoring", "process improvement", "novel concept", "brainstorm", "capture idea"

## Location
`subconscious/ideas/` — pre-existing. DO NOT create.

## Process
1. **Clarify** — WHAT, not HOW. No code, no design.
2. **Capture** — one .md per idea (append if related).
3. **Return** — file path.

## Template
```markdown
---
id: "unique-id"
title: "Concise title"
status: "new"
created: "YYYY-MM-DD"
---
# Idea: [Title]
## What: [Problem or opportunity]
## Target: [Component/file/system]
## Change: [Specific scope]
## Success Criteria: [Definition of done]
## Testing: [Verification steps]
```

## Rules
- Capture only — no implementation or design
- One file per idea

## Helper
```bash
python3 skills/idea/idea_gen.py  # idea helper
```

## Idea → Task Pipeline
```
Idea (subconscious/ideas/) → Task (tasks/1_todo/) → Implementation → Done
```
1. `skill('idea')` — capture
2. `skill('task_creation')` — formalize
3. `skill('dream')` — execute
4. `skill('task')` — verify

## Related Skills
- `plan_template` — Turn ideas into structured plans
- `project-onboard` — Understand project context before ideating
- `task` — Task framework, lifecycle, verification
- `task_creation` — Formalize ideas into executable tasks
- `bug_investigation` — Find improvement ideas from bugs
- `dream` — Dream orchestrator for task execution
- `wiki` — Knowledge storage and retrieval
