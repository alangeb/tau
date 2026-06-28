---
name: tau_audit
description: Analyze Tau log files — agent behavior, errors, loops, tool usage, session patterns, API failures. Audit logs, analyze logs, session review, agent behavior, what went wrong, tool errors, loop detection, session stats (also load: bug_investigation, _taudoc, shell_scripting, tauskillmaintenance)
category: analysis
keywords: audit, analyze, logs, session, behavior, errors, loops, tool usage, API failure, what went wrong
---

# Tau Log Analysis

## When
"analyze audit", "audit file", "context file", "tau log", "session review", "agent behavior", "what went wrong", "tool errors", "loop detection", "session stats", "API failure", "plan file", "analyze logs"

## Entry Types
| Type | Fields |
|------|--------|
| `SESSION_START` | `pid`, `model`, `tools=N`, `cwd`, `nesting`, `version`, `branch`, `hash` |
| `USER` | Content with `  | ` prefix |
| `ASSISTANT` | `content_len=N`, `nesting=N` |
| `TOOL_CALL` | `id=`, `original_name=`, `final_name=`, `fixes=`, `nesting=N` |
| `TOOL_RESULT` | `id=`, `status=success/error`, `duration_ms=`, `bytes=`, `tool=` |
| `TOOL_ERROR` | `id=`, `error_type=RuntimeError/TOOL_NOT_FOUND/TimeoutError/VALIDATION_ERROR` |
| `TOOL_BLOCKED` | `id=`, `tool=`, `available=...` |
| `FORK_START`/`FORK_END` | `task=`, `duration_s=`, `nesting=N` |
| `SUBAGENT_START`/`SUBAGENT_END` | `task=`, `duration_s=`, `nesting=N` |
| `CONSOLE_WARNING` | Content, `nesting=N` |

## Key Patterns
- Content lines: `  | ` prefix (2 spaces + pipe)
- Nesting: `nesting=N` = fork/subagent depth (0 = root)
- Tool pairing: TOOL_CALL + TOOL_RESULT share same `id=`
- Ghost sessions: Many SESSION_STARTs, zero FORK/SUBAGENT → UNHEALTHY
- Phantom tool calls: Unmatched TOOL_CALLs → incomplete operations
- THINK MODE: Restricted tools (end_turn, file_read, glob, grep, info, pyanalyze, pycheck, pyscan, skill)

## Quick Stats
```bash
python3 skills/tau_audit/analyze_audit.py <audit_file>
python3 skills/tau_audit/batch_analyze.py <log_dir> --top 10 --sort errors
python3 skills/tau_audit/audit_analyze.py tools        # Tool usage summary
python3 skills/tau_audit/audit_analyze.py errors       # Error summary
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
- `info` — agent status and context usage
- `web-research` — web content extraction
- `bug_investigation` — root cause analysis
- `context_management` — context windows
- `shell_scripting` — audit log processing
- `reference` — quick lookup for patterns
- `swe_bench` — SWE-bench workflow

- `error-recovery` — Handle tool errors
- `git-advanced` — Advanced git
- `skill_template` — Create new skill or modify existing skills
- `dream` — Dream orchestrator
- `_taudoc` — Maintain TauErgon documentation structure
- `tauskillmaintenance` — Periodic skill maintenance
- `performance` — Performance