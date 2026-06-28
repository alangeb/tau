---
name: idea
description: Capture ideas for features, fixes, improvements. Brainstorm, ideation, idea-to-task pipeline (also load: task, task_creation, plan_template, project-onboard)
category: development
keywords: idea, ideas, brainstorm, ideation, feature idea, bug fix, improvement, capture idea, thought capture, new feature, novel concept, idea pipeline, idea to task, subconscious, ideas folder
---

# Idea Capture

## When
"new feature", "bug fix", "refactoring", "process improvement", "novel concept", "brainstorm", "capture idea", "idea pipeline"

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
- CAPTURE ONLY — no implementation, no design
- One idea per file (append if related)
- Clarify before writing

## Helper
```bash
python3 skills/idea/idea_gen.py  # idea helper
```

## Idea → Task Pipeline
```
Idea (subconscious/ideas/) → Task (tasks/1_todo/) → Implementation → Done
```
1. `skill('idea')` — capture here
2. `skill('task_creation')` — formalize as task
3. `skill('dream')` — execute via dream
4. `skill('task')` — verify status

## Related Skills
- `task` — Complete task framework, lifecycle, verification
- `task_creation` — Formalize ideas into executable tasks
- `dream` — Dream orchestrator that executes tasks
- `plan_template` — Turn ideas into structured plans
- `project-onboard` — Understand project context before ideating
- `bug_investigation` — Find improvement ideas from bugs