---
category: analysis
description: "Analyze session logs, audit agent behavior, detect loops, review tool usage, find errors (also load: grep_tool, reference, shell_scripting, tau_testsuite, bug_investigation, error-recovery, health, info, tauskillmaintenance)"
keywords: session log parsing, TOOL_ERROR pattern matching, ghost session detection, phantom tool call identification, nesting depth tracking
name: tau_audit
---

# Tau Log Analysis

## When
"analyze audit" | "audit file" | "tau log" | "session review" | "agent behavior" | "what went wrong" | "tool errors" | "loop detection" | "session stats" | "API failure" | "analyze logs"

## Entry Types
`SESSION_START` pid, model, tools=N, cwd, nesting | `SESSION_END` duration_s, tool_calls, tokens | `USER` type=manual|synthetic | `ASSISTANT` content_len=N | `TOOL_CALL` id=, original_name=, final_name=, nesting=N | `TOOL_RESULT` id=, status=success/error, duration_ms= | `TOOL_ERROR` error_type=RuntimeError/TOOL_NOT_FOUND/TimeoutError/VALIDATION_ERROR | `TOOL_BLOCKED` tool= | `FORK_START/END` task=, duration_s=, nesting=N | `SUBAGENT_START/END` task=, duration_s=, nesting=N | `COMPRESS_*` bytes_before/after= | `CONTEXT_*` bytes_total= | `LOOP_DETECTION` type=, count=

## Key Patterns
- Content lines: `  | ` prefix
- Nesting: `nesting=N` = fork/subagent depth (0 = root)
- Tool pairing: TOOL_CALL + TOOL_RESULT share same `id=`
- Ghost sessions: Many SESSION_STARTs, zero FORK/SUBAGENT → UNHEALTHY
- Phantom tool calls: Unmatched TOOL_CALLs → incomplete
- THINK MODE: Restricted tools (end_turn, file_read, glob, grep, info, pyanalyze, pycheck, pyscan, skill)

## Quick Stats
```bash
python3 skills/tau_audit/analyze_audit.py <audit_file>           # Single-file, JSON
python3 skills/tau_audit/batch_analyze.py <log_dir> --top 10     # Multi-file
python3 skills/tau_audit/audit_analyze.py tools|errors           # Lightweight
```

## Pattern Search
```bash
grep -c 'TOOL_ERROR\|TOOL_BLOCKED' <audit_file>
grep 'TOOL_ERROR' <audit_file> | grep -oP 'error_type=\K\w+' | sort | uniq -c | sort -rn
grep 'FORK_END' <audit_file> | grep -oP 'duration_s=\K[\d.]+'
grep -oP 'nesting=\K\d+' <audit_file> | sort | uniq -c | sort -rn
```

## Session Types
`simple_tool` Healthy, `.audit` | `normal` Healthy, `.context` | `swe_bench` automated | `ghost` UNHEALTHY, restart loops | `minimal` UNHEALTHY, empty/failed | `orphan` UNHEALTHY, no context | `long_running` Caution, avg 8.3h

PID naming: `{pid}_{YYYYMMDDHHMMSS}_{counter}`

## Analysis Scripts
| Script | Purpose |
|--------|---------|
| `analyze_audit.py` | Single-file, all dimensions, JSON |
| `batch_analyze.py` | Multi-file, sort by errors/duration/health |
| `audit_analyze.py` | Lightweight: `tools`, `errors`, `stats` |
| `content_quality_analysis.py` | Uncertainty, confidence, self-correction |
| `extract_user_messages.py` | TSV: session_prefix, cwd, source, message |
| `fork_subagent_deep_analysis.py` | Fork/subagent patterns, completion |
| `comprehensive_tool_analysis.py` | Tool chains, latency, TOOL_BLOCKED |

## Related Skills
- `bug_investigation` — Root cause analysis
- `debug` — Debug from logs
- `error-recovery` — Error recovery patterns
- `health` — Server health
- `info` — Agent status
- `shell_scripting` — Audit log processing
- `sum` — State summarization
- `tauskillmaintenance` — Periodic skill maintenance
