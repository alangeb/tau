---
name: performance
description: Performance — context window optimization, token counting, tool call latency. Profile, benchmark, optimize, slow, speed, bottleneck, make faster (also load: bug_investigation, tau_audit, context_management)
category: development
keywords: performance, profile, benchmark, optimize, slow, speed, bottleneck, context, token, latency
---

# Performance

## When
"slow code", "performance issue", "profile", "benchmark", "optimize", "bottleneck", "make it faster"

## Tau-Specific Patterns

### Context Window Optimization
- 200K token limit
- >80% usage — compress or delegate
- >90% usage — critical, delegate immediately
- Fork = expensive (full context clone)
- Subagent = cheap (minimal context)

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
- `code-review-workflow` — review code for performance
- `context_management` — context capacity optimization
- `shell_scripting` — system-level performance monitoring
