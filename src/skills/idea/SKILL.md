---
description: "Capture ideas — brainstorm features, document in subconscious/ideas/ with status tracking, convert to tasks (also load: task, plan_template, dream, manifest)"
keywords: idea capture, brainstorm, feature ideas, idea tracking, idea documentation, convert to tasks, idea management, feature planning
name: idea
category: planning
---

# Idea Capture

## When
"new feature" | "bug fix" | "refactoring" | "process improvement" | "novel concept" | "brainstorm" | "capture idea" | "task list"

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
2. `skill('task')` — formalize
3. `skill('dream')` — execute
4. `skill('task')` — verify

## Related Skills
- `manifest` — hierarchical plan tracking, goal management
- `bug_investigation` — Find improvement ideas from bugs
- `dream` — Dream orchestrator for task execution
- `plan_template` — Turn ideas into structured plans
- `project-onboard` — Understand project context before ideating
- `task` — Task framework, lifecycle, verification
- `task` — Formalize ideas into executable tasks
- `wiki` — Knowledge storage and retrieval
