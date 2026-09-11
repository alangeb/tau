---
category: testing
description: "Run tests in background tmux and monitor test suite, detect failures — background_wait with keywords (also load: background, shell_scripting, swe_bench, tau_testsuite, tmux_monitoring)"
keywords: async tmux test execution, status.json polling, completion keyword detection, idle timeout configuration, test result aggregation
name: test-suite-monitor
---

# Test Suite Monitor

## When
"run tests", "monitor tests", "run test suite", "background tests", "background testing"

## Sequence
```bash
# Start
background_new(command="cd $HOME/tau/test && ./run")
# Poll — wait 120s min between checks
background_capture {"session_name": "...", "lines": 10}
# Detect done: "can't find pane" = ended, or "Test Suite Completed!" in output
# Report
find $HOME/tau/test/output -name "status.json" | xargs grep '"status"' | sort | uniq -c
```

## Timing
- `sleep 120` min between polls
- Use `background_wait` with keywords: `error|warning|complete|done|FAILED|SUCCESS|PASSED|Traceback|Exception`

## Helper
```bash
python3 skills/test-suite-monitor/test_monitor.py
```

## Related Skills
- `background` — tmux session management
- `tmux_monitoring` — polling best practices
- `tau_testsuite` — test structure and helpers
- `swe_bench` — benchmark evaluation pipeline
