# Delegate Mode

Delegate mode is an **orchestrator mode** for task delegation. The agent plans and delegates work via `fork` and `subagent` tools, but does NOT do work itself (no file edits, no shell commands, no writes).

## Usage

```
/delegate <task description>
```

Example:
```
/delegate Review the entire heartbeat implementation and fix any bugs
```

## How It Works

### Loop Mechanics

1. **First turn**: `invoke_with_tools(task + DELEGATE_INSTRUCTIONS)`
   - LLM plans and delegates subtasks
   - Returns when LLM ends turn (end_turn tool, ENDOFTURN sentinel, or budget)

2. **Continue loop**: Only runs if the turn was interrupted (`result is None`).
   - Injects `"Continue TASK"` to prompt more delegation work
   - Max 10 iterations (safety limit)

3. **Exit condition**: The loop exits when `invoke_with_tools()` returns a
   non-None response. This means the LLM has completed its work and ended
   the turn normally.

### Tool Restrictions

Delegate mode restricts tools to read/analysis + delegation only:

**Allowed:**
- Delegation: `fork`, `subagent`
- Read/analysis: `glob`, `file_read`, `pyscan`, `grep`, `info`, `plan`, `skill`, `wc`, `head`, `ls`, `pygraph`, `pyanalyze`, `pycheck`
- Turn control: `end_turn`

**Blocked:** Everything else (file_write, bash, background_run, etc.)

The tool filter is applied at execution time. All tools are still announced to the LLM (prefix cache preserved), but non-allowed tools are blocked when called with a denied message.

### Design Notes

- The LLM is instructed to track progress itself and respond when done
- There is no iteration limit — the LLM decides when to stop
- The continue loop exists to handle cases where the turn is interrupted
- Max 10 iterations as a safety limit to prevent infinite loops

## Bug Fix History

### 2025-01-15: Fixed infinite loop bug

**Problem:** The old code checked `while agent.force_end_turn is None`. This was WRONG because `force_end_turn` is only set by external intervention (`+stop` steering, loop escalation). It is NOT set by the normal EOT flow.

**Result:** If the LLM ended the turn normally, `force_end_turn` remained `None`, and the loop kept injecting "Continue TASK" forever.

**Fix:** Changed loop condition to `while result is None`. Only continues if the turn was interrupted. Exits for any other case (normal response or error). Added max iteration limit (10) as a safety net.

## Implementation

- **Command file:** `commands/delegate.py`
- **Tests:** `tests/test_delegate.py`
- **Tool filter:** `agent_tool_filter.py`
- **EOT flow:** `agent_loop.py` (run_loop function)

## Related

- [Architecture](ARCHITECTURE.md)
- [Commands](COMMANDS.md)
- [Tools](TOOLS.md)