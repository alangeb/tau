# Context Management

**See also**: [ARCHITECTURE.md](ARCHITECTURE.md) (module inventory), [EOT.md](EOT.md) (end-of-turn contract), [INDEX.md](INDEX.md) (design index)

## Common Patterns

```python
# Append messages (maintains alternation)
# All user messages are auto-prefixed with [U:TYPE | N:stack]
agent.context.append_user("User message")  # → [U:real | N:0] User message
agent.context.append_user("Fork task", user_type="fork")  # → [U:fork | N:F] Fork task
agent.context.append_assistant("Assistant response", tool_calls=None)
agent.context.append_tool("Tool result", tool_call_id="xxx")

# Synthetic user message AFTER tool results (requires bridge!)
# WRONG: ctx.append_synthetic_user("category", "content")  # violates alternation
# RIGHT: use the bridge helper
ctx.append_synthetic_user_with_bridge("category", "content")

# Synthetic user message AFTER assistant (no bridge needed)
ctx.append_synthetic_user("category", "content")

# Check context size
tokens = agent.context.estimate_tokens(pending_tokens=0)
agent.context.compress(0.30, agent, tools)  # Target 30% reduction

# Get byte size (cached, invalidated on mutation)
bytes = agent.context.bytes_size()

# Deep copy context (for forks)
ctx_copy = agent.context.copy()  # Full deep copy, independent messages
```

## Performance Notes

### `bytes_size()` Caching

`bytes_size()` returns the JSON-serialized byte size of the context. The result is cached and invalidated on every mutation (append, clear, extend, undo, set_messages, merge, cleanup_synthetic, close_turn). This avoids O(n) JSON serialization on repeated calls.

### `copy()` Deep Copy Semantics

`copy()` performs a full `copy.deepcopy()` of the messages list. This ensures fork contexts are completely independent — no shared message dicts or nested structures (tool_calls, function dicts, etc.).

### `_prepare_messages()` Tool Calls Isolation

In `agent_llm_invoke.py`, `_prepare_messages()` deep copies `tool_calls` before stripping non-API fields. This prevents mutation of the original context's tool_calls dicts.

## User Message Prefix Protocol

All user messages are prefixed with `[U:TYPE | N:stack]` to indicate source and nesting level:

| Type | Meaning | Synthetic? |
|------|---------|-----------|
| `real` | Actual user input (CLI/stdin) | No |
| `meta` | System metadata (bridges, turn markers) | Yes |
| `confirm` | End-of-turn confirmation requests | Yes |
| `inject` | Parent injection via control queue extension point | Yes |
| `system` | System-injected (escalation, recovery) | Yes |
| `fork` | Fork task (from /fork command) | No |
| `subagent` | Subagent task (from /subagent command) | No |
| `redirect` | Redirect command (clear + new task) | No |

**Nesting stack:** `0` (root), `F` (fork), `S` (subagent), `SF` (fork in subagent), etc.

**Key distinction:** `meta`, `confirm`, `inject`, `system` are synthetic (removed by `cleanup_synthetic()`). `real`, `fork`, `subagent`, `redirect` are NOT synthetic (preserved across turns).

```python
# Synthetic user messages (auto-prefixed via category mapping)
ctx.append_synthetic_user("eot_confirmation", "Confirm...")  # → [U:confirm | N:0] Confirm...
ctx.append_synthetic_user("continuation", "Continuing...")   # → [U:meta | N:0] Continuing...
ctx.append_synthetic_user("escalation", "You are looping...")  # → [U:system | N:0] You are looping...

# Non-synthetic user messages (explicit type)
ctx.append_user("Task", user_type="fork")      # → [U:fork | N:F] Task
ctx.append_user("Task", user_type="subagent")  # → [U:subagent | N:S] Task
ctx.append_user("Task", user_type="redirect")  # → [U:redirect | N:0] Task
```

## Synthetic Bridge Cleanup & Explicit Merge

After synthetic bridges are removed, consecutive assistant messages may appear.
The merge is **explicit** — the caller decides when to merge. See **DECISIONS.md §18.7** for rationale.

```python
# Remove synthetic bridges only (no automatic merge)
ctx.cleanup_synthetic()

# Explicitly merge consecutive assistant messages (optional, caller decides)
ctx.merge_consecutive_assistants()
```

**Merge behavior:** `merge_consecutive_assistants()` merges assistant and user messages.
Consecutive assistant messages are merged (content, tool_calls deduplicated by ID, reasoning, refusal, usage_metadata summed).
Consecutive user messages are merged gracefully (content concatenated) with a warning logged.
Consecutive tool messages are NOT merged — each tool result has a unique tool_call_id/name.

- **assistant**: Merge `content`, `tool_calls` (deduplicated by ID), `reasoning`, `refusal`, `usage_metadata` (summed)
- **user**: Merge `content` (concatenated with newline), log warning
- **tool**: NOT merged — preserved as separate messages (batched tool calls)

**Used in `close_turn()`:**
```python
def close_turn(self, reason):
    self.cleanup_synthetic()           # remove bridges
    self.merge_consecutive_assistants()  # explicit merge after cleanup
```

## Synthetic Bridge Requirement

**MANDATORY:** When adding a synthetic user message after tool results, a synthetic assistant message MUST be added first. This maintains OpenAI alternation compliance (see **DECISIONS.md §18.6**).

```python
# WRONG - violates alternation (tool → user without assistant)
ctx.append_synthetic_user("category", "content")

# RIGHT - full bridge (tool → assistant → user)
ctx.append_assistant("[Processing...]", synthetic=True)
ctx.append_synthetic_user("category", "content")

# BEST - use the bridge helper (atomic, always correct)
ctx.append_synthetic_user_with_bridge("category", "content")
```

**Bridge patterns by context state:**
- **After tool results:** assistant bridge → synthetic user (BRIDGE REQUIRED)
- **After assistant (no tools):** synthetic user directly (no bridge needed)
- **After user (real or synthetic):** assistant bridge → synthetic user (BRIDGE REQUIRED)

**When to use the bridge helper:**
- Control queue inject (`_process_control_queue()`)
- Loop escalation injection (`inject_reflection()`, `inject_early_reflection()`)
- Any code path that injects synthetic user messages during tool execution

**When the bridge is NOT needed:**
- After assistant message with no tool calls (EOT confirmation flow)
- After context clear (redirect flow)
- At the start of a turn (normal user input)

## Subagent Invocation

```python
# Fork — inherits full context
from agent_subagent import invoke_fork_sync
result = invoke_fork_sync(
    prompt="Review the changes",
    parent_context=agent.context,
    parent_agent=agent,
    nesting_stack=agent.nesting_stack,
    nesting_type="F",
    tool_call_id=None,
    tool_filter=None,
    config=agent.config,
    nesting_threshold=agent.config.nesting.depth_threshold,
)

# Subagent — blank slate
from agent_subagent import invoke_subagent_sync
result = invoke_subagent_sync(
    prompt="Write a unit test",
    system_prompt="You are a testing assistant",
    parent_agent=agent,
    nesting_stack=agent.nesting_stack,
    nesting_type="S",
    tool_filter=None,
    config=agent.config,
    nesting_threshold=agent.config.nesting.depth_threshold,
)
```

**Nesting stack:** Tracks delegation depth via string concatenation (e.g., `"SF"` = subagent → fork). Depth is `len(nesting_stack)`. Nesting restrictions apply when depth ≥ `nesting_threshold - 1`.

## End-Turn

The EOT (End-of-Turn) protocol is documented in **EOT.md**. This section
summarizes the key flows; see EOT.md for the full contract.

**Normal flow:**
- Model returns text with tool calls → tools execute, loop continues
- Model returns text with `end_turn` → turn ends immediately
- Model returns plain text ending with `ENDOFTURN` → self-confirming, turn ends immediately (sentinel stripped)
- Model returns plain text (no tools, no `end_turn`, no sentinel) → confirmation round

**Self-confirming end-of-turn:**
- Model returns plain text ending with `ENDOFTURN` sentinel
- Sentinel is stripped; preceding content is used as final response
- Turn ends immediately — no confirmation round needed
- Audit event `EOT_SELF_CONFIRMED` is emitted

**Confirmation round (when self-confirmation is not used):**
- System injects synthetic user message asking for confirmation
- Model must reply with `ENDOFTURN` sentinel as plain text (no tool call)
- Or model continues with tool calls → rewind and process them
- If budget exhausted (20 attempts), best-effort response is returned

**Key invariants:**
- EOT state resets at start of each `run_loop()`
- Confirmation stack holds messages across multiple rounds
- `last_substantive_response` only updates when NOT in recovery mode
- Restricted nesting (T/K types) bypasses confirmation
- Sentinel string assembled from parts at runtime (prevents LLM pattern learning)

See **EOT.md** for full state diagram, response selection priority, entry points,
pre-flight size check, error handling, and audit events.
