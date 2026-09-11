---
category: development
description: "Systematic bug investigation and root cause analysis — investigate with pyscan, pyanalyze, grep, traceback (also load: debug, tau_audit, file-ops, pyprep, think)"
keywords: root cause identification, pyscan structural scan, pyanalyze usage check, hypothesis-driven investigation, systematic fault isolation, traceback parsing, pattern search, file inspection
name: bug_investigation
---

# bug_investigation

## When
"investigate bug" "root cause" "debug" "why does this fail" "diagnose" "error" "traceback" "investigate error" "trace error" "find root cause" "traceback analysis" "error tracing" "fault isolation" "debug error"

## Tool Sequence (ALWAYS first)
1. `pyscan(path=".")` — structural inventory
2. `pyanalyze(path=".")` — unused functions/imports
3. `grep` — pattern search, call sites, execution paths

## Process
1. **Capture** — reproduce error, save traceback
2. **Search** — `grep -rn "error_keyword" . --include="*.py"`
3. **Inspect** — `file_read` relevant files around error line
4. **Trace** — follow call chain: `grep -rn "function_name(" . | grep -v "def "`
5. **Hypothesize** — form theory from evidence
6. **Verify** — test hypothesis with minimal change
7. **Fix** — apply fix, verify tests pass

## Common Root Causes
- Return value ignored in call chain
- Thread target not detected by AST tools
- State not passed between layers
- Assumption violation (expected vs actual)

## Quick Patterns
```bash
# Find error source
grep -rn "ERROR\|Exception\|Traceback" . --include="*.py"

# Find callers
grep -rn "function_name(" . --include="*.py" | grep -v "def function_name"

# Find recent changes
git log --oneline -10 -- <file>

# Check for similar errors
grep -rn "similar_pattern" ~/.local/tau/log/*.audit
```

## Checklist
- [ ] pyscan + pyanalyze + grep run
- [ ] Error reproduced and captured
- [ ] Pattern searched across codebase
- [ ] Call chain traced
- [ ] ≥2 hypotheses tested
- [ ] Root cause identified
- [ ] Fix proposal with specific changes
- [ ] Verification plan defined

## Helper
```bash
python3 skills/bug_investigation/investigate.py <func_name>  # Automated investigation report
python3 skills/bug_investigation/parse_traceback.py <traceback.txt>  # Parse traceback
```

## Related Skills
- `ast-grep` — structural pattern search
- `debug` — systematic debugging workflow
- `error-recovery` — handle tool errors
- `performance` — profile bottlenecks
- `grep_tool` — trace call sites and execution paths
- `git-advanced` — bisect for bug hunting
- `tau_audit` — analyze error patterns in logs
- `security-audit` — security review
- `swe_bench` — SWE-bench workflow
- `graphify` — graph-based bug analysis
- `pyprep` — Python project prep for debugging
- `think` — deep thinking on bugs
- `docker` — debug container issues
- `health` — diagnose server issues
- `tauskillmaintenance` — skill quality audit
- `idea` — capture improvement ideas
- `plan_template` — plan investigation steps
