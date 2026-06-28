---
name: context_management
description: Manage agent context — fork (full memory), subagent (blank slate), background (async). Delegate, parallel work, context overflow, spawn, background task, memory management (also load: background, think, info)
category: development
keywords: context, fork, subagent, delegate, parallel, overflow, spawn, background, memory, capacity
---

# Context Management

## When
"delegate task", "fork subagent", "background work", "context full", "spawn agent", "delegate", "spawn", "context overflow"

## Fork vs Subagent
| Mode | Memory | Use When |
|------|---------|----------|
| `fork` | Full conversation history | Task needs context, knowledge inheritance |
| `subagent` | Blank slate, task-only | Isolation needed, self-contained task |

## Patterns

### Fork — Inherit Knowledge
```python
fork(task="Analyze X with all current context")
```
- Synchronous — blocks until done
- Inherits ALL conversation history
- Use when task depends on prior decisions

### Subagent — Isolated
```python
subagent(task="Do X independently, here is everything you need: ...")
```
- Synchronous — blocks until done
- Blank slate — knows ONLY what task says
- Use for isolated, well-defined tasks

### Background — Asynchronous
```python
background_new(command="tau.py 'task'")
background_wait(session_name="...", max_seconds=600, idle_seconds=30, keywords="error|warning|done")
```
- Runs in parallel with other work
- Use for long-running, independent tasks

## Context Capacity Rules
- Fork = expensive (full context clone)
- Subagent = cheap (minimal context)
- Background = cheapest (separate process)
- Prefer subagent over fork when possible
- Prefer background over both for fire-and-forget

## Helpers

```bash
python3 skills/context_management/delegation.py  # Delegation analysis
source skills/context_management/context_check.sh  # Context capacity check
```
## Related Skills
- `docker` — container management
- `background` — async task execution
- `plan_template` — break tasks into delegatable units
- `bug_investigation` — delegate investigation to subagent
- `code-review-workflow` — delegate review tasks
- `tau_audit` — analyze agent behavior patterns
- `performance` — context capacity optimization

- `error-recovery` — Handle tool errors
- `info` — Agent status and diagnostics
- `think` — Deep reasoning tool