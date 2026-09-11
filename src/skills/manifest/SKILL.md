---
description: "Create manifests to track goals, tasks, and plans — hierarchical task management with success criteria, auto-verify, block/unblock/next/delete/clear actions (also load: orchestrate, task, spec)"
keywords: manifest, goal tracking, success criteria, verify commands, subtask progress, auto-verify, manifest creation, goal management, plan, make plan, create plan, task list, project plan, plan tool, hierarchical task management, create tasks, add tasks, complete tasks, block tasks, unblock tasks, task status, task progress, next task, task checklist, todo list
name: manifest
category: planning
---

# Manifest Skill — Task Planning & Goal Tracking

## When
"create manifest" | "track goal" | "update manifest" | "manifest tree" | "goal progress" | "delegation manifest" | "verify criteria" | "task list" | "plan" | "make plan" | "create plan" | "project plan" | "plan tool" | "hierarchical tasks" | "task tracking" | "checklist" | "todo list" | "add task" | "complete task" | "block task" | "plan status" | "plan progress" | "next task"

## Storage
`.tau/manifests/manifest-YYYYMMDDHHMMSS.md` — auto-created directory

## Manifest Format
```yaml
---
id: "manifest-YYYYMMDDHHMMSS"
title: "Short title"
goal: "What to achieve"
status: "planning|executing|complete|failed"
depth: 0
parent: null|"parent-manifest-id"
created: "ISO timestamp"
---
```

**Body sections:** `## Goal`, `## Success Criteria` (checkboxes with `Verify: \`cmd\``), `## Subtasks` (numbered checkboxes), `## Progress`

## Tools

### manifest_create
Create new manifest file. Returns path string.
```
manifest_create(goal="...", title="...", success_criteria="line1\nline2", subtasks="line1\nline2", depth=0, parent="")
```
- Creates `.tau/manifests/` if missing
- Auto-generates ID from timestamp
- Preserves pre-formatted checkboxes (`- [ ]`, `- [x]`)

### manifest_update
Update manifest sections with auto-verify on checked items.
```
manifest_update(path="MANIFEST_PATH", section="SECTION", content="NEW_CONTENT")
```

**Sections:** `status`, `success_criteria`, `subtasks`, `progress`

**Actions (operate on subtasks section):**
- `section="block"`, `content="N"` — Block subtask N: `[ ]` → `[?]`
- `section="unblock"`, `content="N"` — Unblock subtask N: `[?]` → `[ ]`
- `section="next"`, `content=""` — Return first pending subtask
- `section="delete"`, `content="N"` — Delete subtask N
- `section="clear"`, `content=""` — Clear all subtasks

- Auto-runs `Verify: \`cmd\`` for items marked `[x]`

### manifest_tree
Show manifest hierarchy as ASCII tree.
```
manifest_tree(root="")  # optional root manifest id or filename
```
- Status icons: ✓ complete, ✗ failed, ⟳ executing, ○ planning
- Parent-child tree with depth labels

## Workflow — Replaces Plan Tool

### Create a plan
```
manifest_create(goal="Fix login bugs", title="Login Bug Fixes", subtasks="- [ ] 1. Fix password reset\n- [ ] 2. Fix session timeout")
```

### Add tasks
```
manifest_update(path="PATH", section="subtasks", content="- [ ] 1. Fix password reset\n- [ ] 2. Fix session timeout\n- [ ] 3. Add rate limiting")
```

### Complete a task
```
manifest_update(path="PATH", section="subtasks", content="- [x] 1. Fixed → Verify: \`pytest tests/test_login.py\`\n- [ ] 2. Fix session timeout")
```

### Block/unblock a task
```
manifest_update(path="PATH", section="block", content="2")    # Block task 2
manifest_update(path="PATH", section="unblock", content="2")  # Unblock task 2
```

### Get next task
```
manifest_update(path="PATH", section="next", content="")
```

### View status
```
manifest_tree()
```

### Delete/clear tasks
```
manifest_update(path="PATH", section="delete", content="2")  # Delete task 2
manifest_update(path="PATH", section="clear", content="")    # Clear all
```

## Notes
- Verification allowlist: grep, ls, pytest, python3, find, cat, head, wc, echo
- State file: `<manifest>.state.json` tracks retry counts
- Checkbox states: `[ ]` pending, `[x]` done, `[?]` blocked

## Related Skills
- `task` — Task management
- `spec` — Spec-driven development, ADR
- `orchestrate` — Goal-driven delegation with manifests
- `dream` — Self-improvement orchestrator

## Helper
```bash
python3 skills/manifest/manifest_gen.py <goal>  # Generate manifest file
```
