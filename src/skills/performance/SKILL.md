---
description: "Profile and optimize speed, find slow bottlenecks — cProfile, token consumption, performance optimization (also load: debug, pyprep, shell_scripting, freecad)"
keywords: performance profiling, cProfile, bottleneck detection, token optimization, tool call latency, context window usage, performance optimization
name: performance
category: python
---

# Performance

## When
"slow code" "performance issue" "profile" "benchmark" "optimize" "bottleneck" "make it faster" "code review" "review code"

## Tau-Specific Patterns

### Context Window
See AGENT.md — CONTEXT MANAGEMENT section. Fork expensive, subagent cheap.

### Tool Call Latency
```bash
grep -oP 'duration_ms=\K[\d]+' <audit_file> | sort -n | tail -10
```

### Token Counting
```bash
grep "content_len=" <audit_file> | grep -oP 'content_len=\K\d+'
```

## Checklist
- [ ] Profiled — identified bottlenecks
- [ ] Measured before/after
- [ ] No regression
- [ ] Documented performance

## Helper
```bash
python3 skills/performance/profile_helper.py  # performance helper
```

## Related Skills
- `bug_investigation` — investigate performance issues
- `context_management` — context capacity optimization
- `code-review-workflow` — review code for performance
- `info` — agent status and diagnostics
- `shell_scripting` — system-level performance monitoring
- `tau_audit` — session log analysis
- `delegation` — optimize token usage
- `freecad` — profile bottlenecks and optimize
- `health` — server health monitoring
- `debug` — debug performance issues
- `error-recovery` — handle errors and recover
