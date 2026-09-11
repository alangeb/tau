---
description: Tau log review — analyze audit logs for errors, patterns, and improvement opportunities
---

# /_taulogreview — Log Review

## Phase 0: Get Audit Files from Registry

### 0.1 Load Audit Files

```bash
# Get audit files from registry (includes archived sessions)
cd src && python3 -c "
from agent_session_registry import get_registry
registry = get_registry()
files = registry.get_audit_files(include_archived=True)
for f in files[:50]:  # Last 50 sessions
    print(f)
" > /tmp/log_audit_files.txt

# Fallback: scan LOG_DIR directly if registry fails
if [ ! -s /tmp/log_audit_files.txt ]; then
  LOG_DIR="$HOME/.local/tau/log"
  ls -t "$LOG_DIR"/*.audit 2>/dev/null | head -50 > /tmp/log_audit_files.txt
fi

echo "Audit files to analyze: $(wc -l < /tmp/log_audit_files.txt)"
```

### 0.2 Filter by Status (Optional)

```bash
# Analyze only active sessions (exclude archived)
cd src && python3 -c "
from agent_session_registry import get_registry
registry = get_registry()
files = registry.get_audit_files(include_archived=False)
for f in files[:50]:
    print(f)
" > /tmp/log_active_audit_files.txt

# Use active files if available, otherwise use all
if [ -s /tmp/log_active_audit_files.txt ]; then
  cp /tmp/log_active_audit_files.txt /tmp/log_audit_files.txt
fi
```

### 0.3 Filter by Tags (Optional)

```bash
# Analyze sessions with specific tags (e.g., "dream" or "test")
cd src && python3 -c "
from agent_session_registry import get_registry
registry = get_registry()
# Search for sessions with 'dream' tag
sessions = registry.search_by_tags(['dream'], match_all=False, include_archived=True)
for s in sessions[:50]:
    audit = s.get('audit')
    if audit:
        print(audit)
" > /tmp/log_tagged_audit_files.txt

# Use tagged files if available
if [ -s /tmp/log_tagged_audit_files.txt ]; then
  cp /tmp/log_tagged_audit_files.txt /tmp/log_audit_files.txt
fi
```

## Phase 1: Error Extraction

### 1.1 Extract Errors and Tracebacks

```bash
# Extract all error lines from recent audit logs
while IFS= read -r audit_file; do
  [ -z "$audit_file" ] && continue
  [ -f "$audit_file" ] || continue
  grep -i "error\|exception\|traceback\|failed\|crash" "$audit_file" 2>/dev/null | \
    grep -v "final_name\|tool_call" | head -10
  echo "--- $(basename $audit_file) ---"
done < /tmp/log_audit_files.txt > /tmp/log_errors.txt
cat /tmp/log_errors.txt
```

### 1.2 Count Error Frequency

```bash
# Count error types (portable grep, no -P flag)
while IFS= read -r audit_file; do
  [ -z "$audit_file" ] && continue
  [ -f "$audit_file" ] || continue
  grep -i "error\|exception\|traceback" "$audit_file" 2>/dev/null
done < /tmp/log_audit_files.txt | \
  grep -oE "(ERROR|Exception|Traceback)[^ ]*" | sort | uniq -c | sort -rn | head -30
```

### 1.3 Extract Tool Call Failures

```bash
# Look for tool calls that returned errors
while IFS= read -r audit_file; do
  [ -z "$audit_file" ] && continue
  [ -f "$audit_file" ] || continue
  grep "returncode\|exit_code\|failed" "$audit_file" 2>/dev/null | \
    grep -v "returncode=0\|exit_code=0"
done < /tmp/log_audit_files.txt | head -30
```

## Phase 2: Pattern Analysis

### 2.1 Identify Repeated Failure Patterns
Group errors into categories:
- **Tool failures** — bash, file ops, background tools
- **LLM errors** — API timeouts, context overflow, parsing failures
- **Command failures** — commands that consistently fail
- **Test failures** — pytest, sanity.sh failures
- **Skill issues** — skills not loading, wrong parameters

### 2.2 Analyze Context Overflow
```bash
# Check for context-related issues
while IFS= read -r audit_file; do
  [ -z "$audit_file" ] && continue
  [ -f "$audit_file" ] || continue
  grep "context.*full\|token.*limit\|context.*overflow\|context.*exceeded" \
    "$audit_file" 2>/dev/null
done < /tmp/log_audit_files.txt | head -20
```

### 2.3 Analyze Timeout Patterns
```bash
# Check for timeout patterns
while IFS= read -r audit_file; do
  [ -z "$audit_file" ] && continue
  [ -f "$audit_file" ] || continue
  grep "timeout\|timed out\|TimeoutExpired" "$audit_file" 2>/dev/null
done < /tmp/log_audit_files.txt | \
  sort | uniq -c | sort -rn | head -20
```

## Phase 3: Improvement Opportunities

### 3.1 Identify Root Causes
For each error category:
1. What is the root cause?
2. Is it a skill issue, command issue, or code bug?
3. Can it be fixed with a prompt change or does it need code changes?

### 3.2 Generate Tasks
Create tasks for recurring issues:
1. Use `queue.sh` to create task files — it is self-aware and always uses the correct absolute path (`/home/user/tau/tasks/1_todo/`). Never use `file_write` with relative paths like `tasks/1_todo/` — that creates files in `src/tasks/1_todo/` (wrong location).
2. Include error pattern, frequency, and proposed fix
3. Prioritize by impact (frequency × severity)

**Path Convention (CRITICAL):** Always use absolute paths (`/home/user/tau/tasks/...`) for ALL task file operations. Never use relative paths like `tasks/` or `../tasks/` — these resolve differently depending on the agent's working directory (`src/`), causing task files to be created in the wrong location.

```bash
# Correct: use queue.sh (self-aware, uses absolute paths)
$HOME/tau/tasks/queue.sh "Fix: API Connection Resilience"

# Verify task file was created in the correct location
ls -la /home/user/tau/tasks/1_todo/
```

## Phase 4: Verification

### 4.1 Check Recent Logs
```bash
# Check last 10 sessions for critical issues (from registry)
head -10 /tmp/log_audit_files.txt | while IFS= read -r audit_file; do
  [ -z "$audit_file" ] && continue
  [ -f "$audit_file" ] || continue
  errors=$(grep -c -i "error\|exception\|traceback" "$audit_file" 2>/dev/null || echo 0)
  echo "$(basename $audit_file): $errors errors"
done | sort -t: -k2 -rn
```

### 4.2 Summary Report
Produce a structured report:
```
=== LOG REVIEW REPORT ===
## Error Summary
- Total errors found: [count]
- Error categories: [list]
- Most frequent: [top 5]

## Pattern Analysis
- Context overflow: [count] occurrences
- Timeouts: [count] occurrences
- Tool failures: [count] occurrences

## Improvement Opportunities
- [actionable items with priority]

## Tasks Created
- [list of task files created]
```

## Hard Rules
- **NEVER** load full audit logs into context — use grep, awk, head
- **ALWAYS** work with small chunks (50kb max per session)
- **ALWAYS** create tasks for recurring issues
- **ALWAYS** produce the structured report