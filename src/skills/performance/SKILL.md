---
name: performance
description: "Performance optimization — context window, profile bottlenecks, token counting, tool call latency. Make faster (also load: bug_investigation, context_management, code-review-workflow, error-recovery, info, shell_scripting, tau_audit)"
category: development
keywords: performance, profile, benchmark, optimize, slow, speed, bottleneck, context, token, latency
---

# Performance

## When
"slow code", "performance issue", "profile", "benchmark", "optimize", "bottleneck", "make it faster"

## Tau-Specific Patterns

### Context Window
- 200K token limit; >80% — compress/delegate; >90% — critical, delegate immediately
- Fork = expensive (full context clone); Subagent = cheap (minimal context)

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
