---
name: test-suite-monitor
description: Run test suite in background, monitor progress, detect completion, report results. Run tests, monitor tests, background tests, background testing (also load: background, tau_testsuite)
category: testing
keywords: test, suite, monitor, background, run tests, progress, completion, results, status
---

# Test Suite Monitor

## When
"run tests", "monitor tests", "run test suite", "background tests", "background testing"

## Sequence
```bash
# Start
background_new(command="cd $HOME/tau/test && ./run")
# Poll (sleep 120 minimum)
background_tail {"session_name": "...", "lines": 10}
# Detect completion
# - "can't find pane" = session ended
# - "Test Suite Completed!" in output
# Report
find $HOME/tau/test/output -name "status.json" | xargs grep '"status"' | sort | uniq -c
```

## Timing
- `sleep 120` minimum between polls
- Watch for session termination or completion messages
- Check `status.json` files for results

## Helper

```bash
python3 skills/test-suite-monitor/test_monitor.py  # test suite monitor helper
```
## Related Skills
- `background` — tmux session management
- `tmux_monitoring` — polling best practices
- `tau_testsuite` — test structure and helpers
