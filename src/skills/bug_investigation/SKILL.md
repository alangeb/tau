---
name: bug_investigation
description: Systematically investigate bugs — pyscan, pyanalyze, grep, hypothesis testing, root cause, fix proposal. Debug, root cause, investigate, trace, why broken, why fails, diagnose, something wrong, error, crash, not working, find bug (also load: code-review-workflow, ast-grep, graphify, python_debugging, think)
category: development
keywords: debug, root cause, investigate, bug, trace, why, broken, fails, diagnose, error, crash, not working, hypothesis, fix
---

# Bug Investigation

## When
"investigate bug", "root cause", "debug issue", "find bug", "why does this fail", "something is broken", "why does it fail", "diagnose", "investigate issue"

## Tool Sequence (ALWAYS first)
1. `pyscan(path=".")` — structural inventory, call relationships
2. `pyanalyze(path=".")` — unused functions/imports, dead code
3. `grep` — pattern search, call sites, execution paths

## Process
1. **Hypothesis**: Formulate specific hypotheses from symptoms + tool output
2. **Verify**: Design tests per hypothesis — grep call sites, trace paths, check state
3. **Root Cause**: Single clear explanation of WHY
4. **Fix**: Type (quick/architectural), Location, Change, Risk
5. **Verify**: Test steps, edge cases, regression tests

## Common Root Causes
- Return value ignored in call chain
- Thread target not detected by AST tools
- State not properly passed between layers
- Assumption violation (expected vs actual)

## Checklist
- [ ] pyscan + pyanalyze + grep run
- [ ] ≥2 hypotheses tested
- [ ] Root cause identified
- [ ] Fix proposal with specific code changes
- [ ] Verification plan defined

## Helper
```bash
python3 skills/bug_investigation/investigate.py <path>  # Automated investigation report
```

## Related Skills
- `swe_bench` — SWE-bench workflow
- `docker` — container management
- `python_debugging` — interactive debugging with background
- `code-review-workflow` — automated code analysis
- `ast-grep` — complex pattern search
- `context_management` — delegate investigation
- `plan_template` — structure investigation steps
- `tau_audit` — analyze agent behavior patterns

- `error-recovery` — Handle tool errors
- `performance` — Performance
- `git-advanced` — Advanced git
- `security-audit` — Security checks
- `idea` — Capture ideas for features
- `think` — Deep reasoning tool
- `graphify` — Turn codebases into persistent knowledge graphs
- `agent-browser` — Browser automation CLI for AI agents