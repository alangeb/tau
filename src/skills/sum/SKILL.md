---
category: documentation
description: "Summarize execution summary and state with status, actions taken, decisions, TODO backlog for context handoff (also load: context_management, task, plan_template)"
keywords: execution summary, state summarization, status report, decisions log, TODO backlog, context handoff, summary generation
name: sum
---

# Sum — State Summarization

## When
"generate summary", "state summary", "execution report", "context handoff", "turn summary", "session recap"

## Quick Start
```bash
python3 skills/sum/sum_state.py generate          # Full state summary
python3 skills/sum/sum_state.py template          # Empty template
python3 skills/sum/sum_state.py git-status        # Git changes only
```

## Summary Structure

### Section 1: Execution Summary
- **Objective** — one sentence, primary goal
- **Status** — COMPLETED / IN-PROGRESS / BLOCKED / FAILED
- **Scope** — modules, files, infra affected

### Section 2: Actions & Outcomes
- Worked — approach, result, paths
- Failed — attempt, error, root cause

### Section 3: Knowledge & Decisions
- Technical insights
- Architectural choices, alternatives considered
- Env changes — packages, vars, migrations

### Section 4: TODO Backlog
- [ ] High priority — immediate next step
- [ ] Medium priority — refactoring, tests
- [ ] Low priority — docs, cleanup

### Section 5: Next Steps
1. First action for next agent
2. Validation steps

## Style
- Specific > general; file paths > descriptions; error messages verbatim > paraphrases
- No vague language ("fixed some bugs"), personal info, or speculation w/o evidence

## Related Skills
- `wiki` — store summaries for future reference
- `documentation` — doc standards and patterns
- `tau_audit` — comprehensive system audit
- `dream` — self-improvement session summaries

## Helper
```bash
python3 skills/sum/sum_state.py  # Generate execution state summary
```
