---
category: planning
description: "Create structured task plan template — phases, checklists, progress tracking, organize work (also load: manifest, orchestrate, sum, task, idea, spec, think)"
keywords: task plan, checklist, phased execution, plan tool, progress tracking, task planning, execution plan, plan structure
name: plan_template
---

# Plan File Structure

## When
"plan file" | "task checklist" | "step-by-step plan" | "task list" | "step by step"

## 8 Sections (in order)
1. **TASK DOCUMENTATION** — Original request + recent updates
2. **PLAN** — Phases with checklists `[ ]`, `[>]`, `[x]`, `[?]`
3. **PYSCAN TREE** — Code structure with line references
4. **REQUIREMENTS** — Low/Medium/High (Purpose, Inputs, Outputs, Side Effects, Errors, Tests, Dependencies)
5. **DECISIONS** — Context, Options, Chosen, Rationale, Trade-offs, Impact
6. **TASKS** — Step-by-step (Action, Tool, Expected, Verification)
7. **QUESTIONS** — Open items
8. **RISKS** — Risk, Probability, Impact, Mitigation

## State Markers
- `[ ]` Not started | `[>]` In progress (max 1) | `[x]` Done | `[?]` Blocked

## Rules
- Max one `[>]` at a time
- Update each session; Every `[x]` → Recent Updates
- Preserve history, never delete

## Quick Queries
```bash
grep -n "\[>\]" PLAN.md   # In-progress
grep -n "\[ \]" PLAN.md   # Pending
grep -n "\[x\]" PLAN.md   # Completed
```

## Helper
```bash
python3 skills/plan_template/plan_gen.py  # plan_template helper
source skills/plan_template/plan_helpers.sh  # plan_progress, plan_pending, plan_done, plan_stats, plan_new
```

## Related Skills
- `code-review-workflow` — plan code review phases
- `idea` — Capture ideas for features
- `think` — Deep reasoning tool
- `bug_investigation` — plan investigation steps
- `context_management` — delegate planned tasks
- `dream` — self-improvement loop
- `task` — Complete task framework
- `spec` — task planning for spec implementation
- `orchestrate` — goal-driven delegation with manifests
- `manifest` — Goal-driven delegation manifests
- `sum` — session state summarization
