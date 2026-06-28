---
name: swe_bench
description: SWE-bench workflow — fix agent, eval pipeline, analysis, artifacts. SWE-bench, SWE-lite, SWE-live, fix agent, eval, patch, benchmark (also load: docker, background, bug_investigation, tau_audit, git)
category: benchmark
keywords: SWE-bench, SWE-lite, SWE-live, fix agent, eval, patch, benchmark, test case, pipeline
---

# SWE-bench Workflow

## When
"SWE-bench", "SWE-lite", "SWE-live", "fix agent", "eval pipeline", "patch creation", "benchmark", "test case"

## Pipeline
```
1. Prepare: docker container + issue file
2. Fix: run tau.py agent in container
3. Patch: extract code changes
4. Eval: re-run project tests
5. Analysis: if eval fails, run analysis agent
6. Artifacts: store stdout, audit, context, patch
```

## Directory Structure
```
artifacts/
├── <test_id>/
│   ├── fix/
│   │   ├── stdout.log
│   │   ├── *.audit
│   │   └── *.context
│   ├── eval/
│   │   └── status.json
│   └── analysis/
│       └── *.md
```

## Key Commands
```bash
./swe_adapter.py --start N --count M --llm cuda --stream
./status.py  # Show results
```

## Eval Rules
- Cannot change tests, evaluation, or rules
- Can change test harness and tau agent
- Patch = diff of code changes only
- Eval = re-run project tests with patch applied

## Gotchas
- Container startup: seconds, not minutes
- Agent output: within seconds of start
- >1min silent = broken
- Truncation: check patch is complete
- Timeout: track separately from failure

## Related Skills
- `docker` — container management
- `background` — run tests in background
- `bug_investigation` — analyze failures
- `tau_audit` — review agent behavior
- `git` — patch management

## Helper
```bash
python3 skills/swe_bench/artifact_check.py  # Show test results summary
```
