---
name: tau_audit
description: "Analyze Tau log files — agent behavior, errors, loops, tool usage (also load: _taudoc, bug_investigation, error-recovery, shell_scripting, tauskillmaintenance, swe_bench)"
category: analysis
keywords: audit, analyze, logs, session, behavior, errors, loops, tool usage, API failure, what went wrong
---

# Tau Log Analysis

## When
"analyze audit", "audit file", "context file", "tau log", "session review", "agent behavior", "what went wrong", "tool errors", "loop detection", "session stats", "API failure", "plan file", "analyze logs"

## Entry Types
| Type | Key Fields |
|------|------------|
| `SESSION_START` | `pid`, `model`, `tools=N`, `cwd`, `nesting`, `version`, `branch`, `hash` |
| `SESSION_END` | `duration_s`, `tool_calls`, `tokens` |
| `USER` | `type=manual\|synthetic`, `source=fork\|subagent` |
| `ASSISTANT` | `content_len=N`, `type=response\|reasoning` |
| `TOOL_CALL` | `id=`, `original_name=`, `final_name=`, `nesting=N` |
| `TOOL_RESULT` | `id=`, `status=success/error`, `duration_ms=`, `bytes=` |
| `TOOL_ERROR` | `error_type=RuntimeError/TOOL_NOT_FOUND/TimeoutError/VALIDATION_ERROR` |
| `TOOL_BLOCKED` | `tool=`, `available=...` |
| `FORK_START/END` | `task=`, `duration_s=`, `nesting=N` |
| `SUBAGENT_START/END` | `task=`, `duration_s=`, `nesting=N` |
| `COMPRESS_*` | `step=`, `bytes_before/after=`, `msgs_before/after=` |
| `CONTEXT_*` | `count=`, `total=`, `bytes_total=` |
| `CONSOLE_*` | Content, `nesting=N` |
| `CONFIG_CHANGE` | `key=`, `old_value=`, `new_value=` |
| `ERROR_RATE_ALERT` | `rate=`, `window_s=` |
| `LOOP_DETECTION` | `type=`, `count=`, `duration_s=` |

## Key Patterns
- Content lines: `  | ` prefix (2 spaces + pipe)
- Nesting: `nesting=N` = fork/subagent depth (0 = root)
- Tool pairing: TOOL_CALL + TOOL_RESULT share same `id=`
- Ghost sessions: Many SESSION_STARTs, zero FORK/SUBAGENT → UNHEALTHY
- Phantom tool calls: Unmatched TOOL_CALLs → incomplete operations
- THINK MODE: Restricted tools (end_turn, file_read, glob, grep, info, pyanalyze, pycheck, pyscan, skill)

## Quick Stats
```bash
python3 skills/tau_audit/analyze_audit.py <audit_file>          # Single-file, all dimensions, JSON
python3 skills/tau_audit/batch_analyze.py <log_dir> --top 10 --sort errors  # Multi-file
python3 skills/tau_audit/audit_analyze.py tools                 # Tool usage summary
python3 skills/tau_audit/audit_analyze.py errors                # Error summary
```

## Pattern Search
```bash
grep -c 'TOOL_ERROR\|TOOL_BLOCKED' <audit_file>
grep 'TOOL_ERROR' <audit_file> | grep -oP 'error_type=\K\w+' | sort | uniq -c | sort -rn
grep 'FORK_END' <audit_file> | grep -oP 'duration_s=\K[\d.]+'
grep -oP 'nesting=\K\d+' <audit_file> | sort | uniq -c | sort -rn
```

## Session Types
| Type | Health |
|------|--------|
| `simple_tool` | Healthy, quick |
| `normal` | Healthy |
| `swe_bench` | Healthy, automated |
| `ghost` | UNHEALTHY, restart loops |
| `minimal` | UNHEALTHY, empty/failed |
| `orphan` | UNHEALTHY, no context |
| `cache_underperforming` | Caution |
| `long_running` | Caution, avg 8.3h |

## Log Files
| File | Purpose |
|------|---------|
| `.audit` | Session log |
| `.context` | Conversation context |
| `.failed_request.json` | Failed API requests |
| `.lr.json` | API request logs |
| `.plan` | Task planning data |

PID-based naming: `{pid}_{YYYYMMDDHHMMSS}_{counter}`

## Analysis Scripts
| Script | Purpose |
|--------|---------|
| `analyze_audit.py` | Single-file, all dimensions, JSON output |
| `batch_analyze.py` | Multi-file, sort by errors/duration/health |
| `audit_analyze.py` | Lightweight: `tools`, `errors`, `stats` commands |
| `content_quality_analysis.py` | Uncertainty, confidence, self-correction |
| `extract_user_messages.py` | TSV: session_prefix, cwd, source, user_message |
| `fork_subagent_deep_analysis.py` | Fork/subagent patterns, completion rates |
| `comprehensive_tool_analysis.py` | Tool chains, latency, TOOL_BLOCKED |

## Related Skills
- `_taudoc` — documentation structure
- `bug_investigation` — root cause analysis
- `shell_scripting` — audit log processing
- `tauskillmaintenance` — periodic skill maintenance
- `swe_bench` — SWE-bench workflow
