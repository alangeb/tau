---
description: "Orchestrate goal-driven delegation with accountability, manifest-based recursive task delegation (also load: manifest, delegation, task, dream, info, plan_template, tauskillmaintenance, background)"
keywords: orchestrate, goal-driven delegation, accountability, manifest delegation, recursive delegation, goal management, task orchestration
name: orchestrate
category: planning
---

# Orchestrate — Goal-Driven Delegation

## When
"goal-driven planning" | "accountability" | "verify before exit" | "recursive delegation" | "manifest-based work" | "task list" | "delegate" | "subagent"

## Tool
`orchestrate(goal="...", max_depth=3, retry_budget=2)` — synchronous, blocking.

## Command
`/orchestrate <goal>` — CLI shim for tool.

## How It Works
1. Fork phase: investigates codebase, creates manifest + context
2. Executor phase: delegates subtasks, verifies with manifest_update
3. Verify loop: blocks exit until manifest complete/failed

## Manifest Structure
```
.tau/manifests/
├── manifest-XXXX.md     # Goal, criteria, subtasks, progress
├── manifest-XXXX.ctx    # Codebase context (static)
└── manifest-XXXX.state.json  # Retry counts (machine-managed)
```

## Depth
ORCHESTRATE(0) → ORCHESTRATE(1) → ORCHESTRATE(2) → LEAF(3+)

## Helper
```bash
python3 skills/orchestrate/manifest_ops.py list   # List manifests
python3 skills/orchestrate/manifest_ops.py show    # Show latest
python3 skills/orchestrate/manifest_ops.py verify  # Check status
```

## Related Skills
- `plan_template` — Manifest format and tools
- `delegation` — Fire-and-forget delegation (simpler)
- `task` — Task framework
- `dream` — Self-improvement orchestrator
- `tauskillmaintenance` — Skill maintenance
- `manifest` — Manifest tools and format
- `info` — agent status during orchestration
