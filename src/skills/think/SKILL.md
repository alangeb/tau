---
name: think
description: Deep reasoning tool — stuck loops, mid-execution reassessment, complex planning, assumption changes. Think hard, deep analysis, reassess, stuck, loop detection, deep thinking, plan carefully (also load: context_management, bug_investigation, plan_template)
category: reasoning
keywords: think hard, deep analysis, stuck, loop detection, reassess, complex planning
---

# Think Tool

## When
"think hard", "deep analysis", "stuck in loop", "reassess", "assumptions changed", "complex planning", "deep thinking", "plan carefully"

## Purpose
Pure reasoning pass. Fork analyzes conversation, returns structured analysis. No tools except end_turn.

## Use Only When
- Stuck in meta-analysis loop (repeatedly asking "what should I do?")
- Task or assumptions changed mid-execution, breaking current plan
- Unexpected results requiring deep re-analysis before acting
- Complex multi-part task benefits from explicit planning pass

## Never Use
- As first step before starting a task — just begin
- For routine analysis — own reasoning sufficient
- As substitute for thinking — this spawns a fork, not free

## Delegation Hierarchy
1. Internal reasoning — always start here
2. Fork — complex tasks needing dedicated analysis pass
3. Think tool — ONLY when internal reasoning fails

## Helper
```bash
python3 skills/think/loop_detection.py <audit_file>  # Detect repeating tool call sequences
```

## Related Skills
- `context_management` — fork vs subagent vs think
- `bug_investigation` — systematic root cause analysis
- `plan_template` — explicit task planning