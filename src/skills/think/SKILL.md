---
category: reasoning
description: "Think deeply, reason through complex problems, reassess assumptions, analyze conversation for stuck loops (also load: context_management, bug_investigation, plan_template, manifest)"
keywords: loop detection via audit grep, assumption change reassessment, conversation structure inspection, planning hierarchy generation, meta-cognitive reflection
name: think
---

# Think Tool

## When
"think hard", "deep analysis", "stuck in loop", "reassess", "assumptions changed", "complex planning"

## Purpose
Pure reasoning pass. Fork analyzes conversation, returns structured analysis. No tools except end_turn.

## Use Only When
- Stuck in meta-analysis loop
- Task/assumptions changed mid-execution, plan broken
- Unexpected results need deep re-analysis
- Complex multi-part task needs explicit planning

## Never Use
- First step — just begin
- Routine analysis — own reasoning sufficient
- Substitute for thinking — spawns fork, costs context

## Delegation Hierarchy
1. Internal reasoning — always first
2. Fork — complex tasks needing dedicated pass
3. Think tool — ONLY when internal reasoning fails

## Helper
```bash
python3 skills/think/loop_detection.py <audit_file>  # Detect repeating tool calls
```

## Related Skills
- `manifest` — hierarchical plan tracking, goal management
- `context_management` — fork vs subagent vs think
- `plan_template` — explicit task planning
