---
name: think
description: "Deep reasoning tool — stuck loops, mid-execution reassessment, complex planning. Think hard, deep analysis, I'm stuck, think through this (also load: context_management, bug_investigation, plan_template)"
category: reasoning
keywords: think hard, deep analysis, stuck, loop detection, reassess, complex planning, I'm stuck, think through this, figure this out, deep reasoning
---

# Think Tool

## When
"think hard", "deep analysis", "stuck in loop", "reassess", "assumptions changed", "complex planning", "deep thinking", "plan carefully"

## Purpose
Pure reasoning pass. Fork analyzes conversation, returns structured analysis. No tools except end_turn.

## Use Only When
- Stuck in meta-analysis loop
- Task/assumptions changed mid-execution, breaking plan
- Unexpected results need deep re-analysis
- Complex multi-part task needs explicit planning

## Never Use
- As first step — just begin
- For routine analysis — own reasoning sufficient
- As substitute for thinking — spawns fork, costs context

## Delegation Hierarchy
1. Internal reasoning — always first
2. Fork — complex tasks needing dedicated pass
3. Think tool — ONLY when internal reasoning fails

## Helper
```bash
python3 skills/think/loop_detection.py <audit_file>  # Detect repeating tool calls
```

## Related Skills
- `bug_investigation` — systematic root cause analysis
- `context_management` — fork vs subagent vs think
- `plan_template` — explicit task planning
