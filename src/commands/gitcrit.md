---
description: Git critique
---

## Git Critique Command

### Phase 1: Code Review
Use the `subagent` tool to run a comprehensive code review:
- Run `pyanalyze` and `pyscan` on the code in local ./ folder
- Use your code-simplifier skill
- Use your review skill
- Use your ast-grep skill
- Look at the current git diff, focus on the last changes
- Review them in detail, critique them, use your skills. Be critical. Focus on root cause, don't address symptoms
- Give a comprehensive summary about the changes you see in code

### Phase 2: Issue Review
Use the `fork` tool to carefully review the issue list or improvement suggestions:
- Make sure you really understand them
- Think hard. Derive a new list. Focus on root cause, don't address symptoms
- Give a comprehensive summary about what you found

### Phase 3: Cross-Reference & Documentation Audit
After reviewing code changes, audit for stale references and documentation drift:
1. For every file deleted or renamed in the diff, run `grep -rn` across the entire codebase to find stale references in:
   - Documentation files (README.md, TAU.md, designs/)
   - Skill metadata (skills/*/SKILL.md — "also load" fields)
   - Command files (commands/*.md)
   - Test files (tests/*.py)
   - Configuration files (tau.json, etc.)
2. If changes affect user-facing behavior, commands, or skills:
   - Update TAU.md command/skill inventory
   - Update README.md if relevant
   - Update skill "also load" references
   - Update _tauskillmaintenance.md inventory
3. Report: List ALL stale references found with file:line and the fix needed.
