---
name: context_management
description: "Monitor and manage agent context — token usage, context window, output size control. Prevent overflow with context-aware tool args, compact output, proactive delegation (also load: background, info, bug_investigation, code-review-workflow, error-recovery, performance, think)"
category: development
keywords: context, fork, subagent, delegate, parallel, overflow, spawn, background, memory, capacity, token, limit, compression, monitoring
---

# Context Management

## When
"delegate task", "fork subagent", "background work", "context full", "spawn agent", "delegate", "spawn", "context overflow", "token limit", "context usage", "compression"

## Fork vs Subagent vs Background
| Mode | Memory | Cost | Use When |
|------|---------|------|----------|
| `subagent` | Blank slate | Cheap (1x) | Well-defined task, no context needed |
| `fork` | Full conversation | Expensive | Task needs your knowledge/history |
| `background` | Separate process | Cheapest (1x) | Async, long-running, independent |

### Subagent — Isolated (PREFER)
```python
subagent(task="Read file.py, analyze function X, report findings")
```
Synchronous, blocks. Blank slate — knows ONLY task content. Use: code review, analysis, testing, file edits, refactoring.

### Fork — Inherit Knowledge
```python
fork(task="Continue working on X with all current context")
```
Synchronous, blocks. Inherits ALL conversation history. Use: task depends on prior decisions, complex multi-step work.

### Background — Async
```python
background_run(command="tau.py 'task'", timeout=300, keywords="error|done|FAILED")
```
Parallel. Use: long-running builds, tests, data processing. See `background` skill.

## Context Monitoring
```
info  # Token Usage: XXXXX / 180000 tokens (XX%)
```

### Thresholds
| Usage | Action |
|-------|--------|
| < 30% | Normal |
| 30-50% | Start delegating |
| 50-70% | AGGRESSIVELY delegate |
| 70-85% | STOP non-critical; delegate everything |
| 85%+ | Compression triggers (quality degrades) |

## Keep Tool Output Small
```python
# File reading
file_read(file_path="large_file.py", limit=100)
file_read(file_path="large_file.py", offset=500, limit=50)

# Code analysis — ALWAYS use compact for large projects
pyscan(path=".", compact=True)  # ~60% smaller
pyscan(path=".", compact=True, max_files=20)  # Limit to 20 largest
grep(pattern="def ", path=".", max_results=20)

# Web content
fetch(url="...", max_length=5000)
fetch(url="...", metadata_only=True)
```

**pyscan output size guide:**
- `< 50 files`: `pyscan(path=".")` — full output fine
- `50-200 files`: `pyscan(path=".", compact=True)`
- `> 200 files`: `pyscan(path=".", compact=True, max_files=20)`
- Truncated: follow 💡 Tip in truncation warning

## Delegation Patterns
### Split Large Tasks
```python
subagent(task="Analyze file A")
subagent(task="Analyze file B")
# Synthesize results (small context)
```

### Delegate Review
```python
subagent(task="Run code review on ./src/: pyscan compact, pygraph, pyanalyze, git diff, report")
```

### Background Long Tasks
```python
background_run(command="./sanity.sh", timeout=180, keywords="PASSED|FAILED|error")
```

## Anti-Patterns (AVOID)
- Reading entire large files — use limits
- Multiple large tools per turn — split or delegate
- Doing delegatable work yourself — subagent is cheaper
- Ignoring context percentage — check `info` regularly
- Waiting for compression — loses information
- Forking when subagent suffices — fork is expensive
- Holding context for "later" — delegate now

## Helpers
```bash
python3 skills/context_management/delegation.py  # Delegation analysis
source skills/context_management/context_check.sh  # Context capacity check
```

## Related Skills
- `background` — async task execution
- `delegation` — delegation strategy and patterns
- `info` — agent status and context usage
- `bug_investigation` — delegate investigation to subagent
- `code-review-workflow` — delegate review tasks
- `error-recovery` — handle tool errors
- `performance` — profile bottlenecks and optimize
- `think` — deep reasoning tool
