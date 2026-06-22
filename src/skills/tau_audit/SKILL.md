---
name: tau_audit
description: Analyze Tau log files (.audit, .context, .json, .plan) — agent behavior, errors, loops, tool usage, session patterns, API failures, task planning (also load: skill_template, tauskillmaintenance, _taudoc, error-recovery, web-research, git-advanced)
category: analysis
---

# Tau Log Analysis

## When
"analyze audit", "audit file", "context file", "tau log", "session review", "agent behavior", "what went wrong", "tool errors", "loop detection", "session stats", "API failure", "plan file"

## Entry Types

| Type | Fields |
|------|--------|
| `SESSION_START` | `pid`, `model`, `tools=N`, `cwd`, `nesting`, `version`, `branch`, `hash` |
| `USER` | Content with `  | ` prefix |
| `ASSISTANT` | `content_len=N`, `nesting=N` |
| `TOOL_CALL` | `id=`, `original_name=`, `final_name=`, `fixes=`, `nesting=N` |
| `TOOL_RESULT` | `id=`, `status=success/error`, `duration_ms=`, `bytes=`, `tool=`, `nesting=N` |
| `TOOL_ERROR` | `id=`, `error_type=RuntimeError/TOOL_NOT_FOUND/TimeoutError/VALIDATION_ERROR` |
| `TOOL_BLOCKED` | `id=`, `tool=`, `available=...` |
| `LLM_CALL` | `model=`, `max_tokens=`, `temperature=`, `nesting=N` |
| `FORK_START`/`FORK_END` | `task=`, `duration_s=`, `nesting=N` |
| `SUBAGENT_START`/`SUBAGENT_END` | `task=`, `duration_s=`, `nesting=N` |
| `CONSOLE_WARNING` | Content, `nesting=N` |

## Key Patterns
- Content lines: `  | ` prefix (2 spaces + pipe)
- Tool schema: Embedded in SESSION_START as JSON array
- Nesting: `nesting=N` = fork/subagent depth (0 = root)
- Tool pairing: TOOL_CALL + TOOL_RESULT share same `id=`
- Nested sessions: SUBAGENT_START → SESSION_START → ... → SUBAGENT_END
- Content errors dominate (2,086/2,086 across 10K files — NOT tool execution failures)
- Tool reliability: 100% across 74,462 tool results (0 tool-level errors)
- Ghost sessions: 996 (9.9%) — many SESSION_STARTs, zero FORK/SUBAGENT markers
- Phantom tool calls: 5,489 unmatched TOOL_CALLs (incomplete operations)

## Quick Stats

```bash
# Single file
python3 skills/tau_audit/analyze_audit.py <audit_file>

# Batch
python3 skills/tau_audit/batch_analyze.py /home/alangeb/.local/tau/log/ --top 10 --sort errors
```

## Pattern Search

```bash
# Errors
grep -c 'TOOL_ERROR\|TOOL_BLOCKED' <audit_file>
grep 'TOOL_ERROR' <audit_file> | grep -oP 'error_type=\K\w+' | sort | uniq -c | sort -rn

# Ghost sessions
ss=$(grep -c 'SESSION_START' <audit_file>); forks=$(grep -c 'FORK_START' <audit_file>); subs=$(grep -c 'SUBAGENT_START' <audit_file>)
# SESSION_STARTs >> (forks + subs) = ghost sessions

# Forks/subagents
grep -c 'FORK_START\|SUBAGENT_START' <audit_file>
grep 'FORK_END' <audit_file> | grep -oP 'duration_s=\K[\d.]+'

# Nesting
grep -oP 'nesting=\K\d+' <audit_file> | sort | uniq -c | sort -rn

# LLM calls (>100 = potential loop)
grep -c 'LLM_CALL' <audit_file>

# Cache warnings
grep 'CONSOLE_WARNING' <audit_file> | grep -c 'cache'
```

## Session Types

| Type | Count | % | Notes |
|------|-------|---|-------|
| `simple_tool` | 7,065 | 70.4% | Healthy, quick |
| `ghost` | 1,003 | 10.0% | UNHEALTHY, restart loops |
| `minimal` | 678 | 6.8% | UNHEALTHY, empty/failed |
| `orphan` | 447 | 4.5% | UNHEALTHY, no context |
| `normal` | 329 | 3.3% | Healthy |
| `swe_bench` | 209 | 2.1% | Healthy, automated |
| `cache_underperforming` | 128 | 1.3% | Caution |
| `long_running` | 37 | 0.4% | Caution, avg 8.3h |

## Common Patterns

1. **Simple**: SESSION_START → USER → ASSISTANT → TOOL_CALL → TOOL_RESULT → end_turn
2. **Fork-heavy**: FORK_START → nested SESSION_START → ... → FORK_END
3. **Think mode**: TOOL_BLOCKED entries, restricted tools only
4. **Debug**: Many TOOL_ERROR, repeated TOOL_CALL, high LLM_CALL
5. **Cache**: Many CONSOLE_WARNING with "cache: low"
6. **Background**: background_new/exec/tail/kill, hours-long
7. **SWE-bench**: cwd='/home/alangeb/swe', 0 ASSISTANT, 50+ LLM_CALL
8. **Tool-only**: 797 sessions (7.9%), 0 assistant responses
9. **Context-driven**: 82.8% have context files; size ∝ error count
10. **API failure**: 304 sessions (3.0%), 76.5% model API failures

## Edge Cases
- Negative durations: LLM_CALL before SESSION_START (previous session data)
- 0 assistant turns: Tool-only sessions, SWE-bench
- THINK MODE: Restricted tools (end_turn, file_read, glob, grep, info, pyanalyze, pycheck, pyscan, skill)
- Phantom tool calls: XML/JSON tool-call-like text with no matching TOOL_CALL
- Multiple SESSION_START per file: Fork/subagent spawning

## Log Files

| File | Purpose | Count |
|------|---------|-------|
| `.audit` | Session log | Primary |
| `.context` | Conversation context | 8,316 (82.8%) |
| `.failed_request.json` | Failed API requests | 306 |
| `.lr.json` | API request logs | 1,766 |
| `.plan` | Task planning data | 291 |

PID-based naming: `{pid}_{YYYYMMDDHHMMSS}_{counter}`

## Analysis Scripts

| Script | Purpose |
|--------|---------|
| `analyze_audit.py` | Single-file, all dimensions, JSON output |
| `batch_analyze.py` | Multi-file, sort by errors/duration/health |
| `content_quality_analysis.py` | Uncertainty, confidence, self-correction |
| `extract_user_messages.py` | TSV: session_prefix, cwd, source, user_message |
| `fork_subagent_deep_analysis.py` | Fork/subagent patterns, completion rates |
| `deep_error_analysis.py` | Error types, recovery, clustering |
| `deep_error_analysis_v2.py` | Improved error detection |
| `comprehensive_tool_analysis.py` | Tool chains, latency, TOOL_BLOCKED |

## Environment
- Worktrees: `/home/alangeb/tau` (master), `/home/alangeb/tau-dev1` (tau-dev1)
- Model: `http://spark:8001/v1`, 200K context
- Test suite: `sanity.sh` at `/home/alangeb/tau-dev1/src/sanity.sh` (100s)
- CWD: `/home/alangeb/tau-dev1/src/`
- Log dir: `~/.local/tau/log`
- TAU_LOG_DIR: Test logs to `~/.local/tau/logtest`

## Related Skills
- `skill_template` — skill creation/modification
- `tauskillmaintenance` — audit and maintain skills
- `bug_investigation` — root cause analysis
- `context_management` — context windows
- `_taudoc` — documentation structure
