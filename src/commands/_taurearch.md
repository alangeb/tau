---
description: Tau re-architecture
---

### Phase 1: Code Analysis
Run `pyscan`, `pygraph`, `pyanalyze`, `pycheck` on the codebase to understand structure.
Use your ast-grep and code-simplifier skills.

**ANALYSIS LIMIT: Maximum 4 analysis tool calls. After 4 calls, you MUST start implementing.**

Review the entire code architecture, ensure you understand the code.
Assume the implementation is correct, especially edge cases, assume they are implemented with purpose.

Your task is to review the architecture of the project.
Decide on one thing to improve. Be careful not to miss edge cases. You can create new files, move code, clean up interfaces, encapsulate code, inline, standardize - whatever most important.

**MANDATORY: After deciding what to improve, immediately start implementing. Do NOT create elaborate plans. Do NOT analyze further. Implement directly.**

Use your manifest tool to create tasks to improve/fix the one most important thing. Do not change functionality. Assume everything is done for a purpose. But do make it more clean.

Then execute on all the changes. Implement the changes.

Heavily rely on subagent and fork: Do only what you must yourself, delegate the rest to fork or subagent.

### Phase 2: Git Review & Documentation Audit
Use the `subagent` tool to run a comprehensive code review:
- Run `pyanalyze` and `pyscan` on the code in local ./ folder
- Use your code-simplifier skill
- Use your review skill
- Use your ast-grep skill
- Look at the current git diff, focus on the last changes
- Review them in detail, critique them, use your skills. Be critical. Focus on root cause, don't address symptoms
- Give a comprehensive summary about the changes you see in code

Then use the `fork` tool to carefully review the issue list or improvement suggestions:
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

### Phase 4: Testing
Run pytests, sanity tests. Fix code if it is broken.
Report on what was done.
