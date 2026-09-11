---
description: "SWE-bench evaluation and benchmark — prepare container, run agent, extract patch, docker testbed (also load: background, test-suite-monitor, dependency_management)"
keywords: SWE-bench Lite evaluation, docker container testbed, patch diff extraction, test suite re-run, artifact storage, issue file parsing
name: swe_bench
category: testing
---

# SWE-bench Workflow

## When
"SWE-bench", "SWE-lite", "SWE-live", "fix agent", "eval pipeline", "patch creation", "benchmark"

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
- Truncation: check patch complete
- Timeout: track separately from failure

## Helper
```bash
python3 skills/swe_bench/artifact_check.py  # Show test results summary
```

## Related Skills
- `docker` — container management
- `background` — run tests in background
- `bug_investigation` — analyze failures
- `tau_audit` — review agent behavior
- `git` — patch management
