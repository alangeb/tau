# EOT (End-of-Turn) Contract

This document defines the End-of-Turn (EOT) protocol. It is the single source
of truth for how turns terminate, how confirmations work, and what invariants
hold throughout the EOT flow.

**Related:** [CONTEXT.md](CONTEXT.md) (context management), [DECISIONS.md](DECISIONS.md) §18.8-18.19 (rationale), [ARCHITECTURE.md](ARCHITECTURE.md) (module inventory), [INDEX.md](INDEX.md) (design index)

---

## States & Transitions

```
                    ┌─────────────────────────────────────────────────────┐
                    │                   NORMAL TURN                        │
                    │  LLM returns tool calls → execute → loop continues   │
                    └──────────────────────────┬──────────────────────────┘
                                               │
                              LLM returns plain text (no tool calls)
                                               │
                    ┌──────────────────────────▼──────────────────────────┐
                    │              POTENTIAL EOT CHECK                      │
                    │  1. Slash command? → dispatch, stay in turn          │
                    │  2. Self-confirming ENDOFTURN? → turn ends           │
                    │  3. Restricted nesting (T/K)? → accept, turn ends    │
                    │  4. Budget exhausted? → force close, turn ends       │
                    │  5. None of above → enter CONFIRMATION               │
                    └──────────────────────────┬──────────────────────────┘
                                               │
                    ┌──────────────────────────▼──────────────────────────┐
                    │              CONFIRMATION ROUND                       │
                    │  Synthetic user message injected asking LLM to       │
                    │  confirm or continue. Held message on stack.         │
                    │                                                      │
                    │  LLM returns:                                       │
                    │  - ENDOFTURN sentinel → accept_confirmation()        │
                    │  - end_turn tool → resolve, close turn               │
                    │  - Tool calls → rewind_with_tools(), loop continues  │
                    │  - Plain text → stack another confirmation           │
                    └──────────────────────────┬──────────────────────────┘
                                               │
                    ┌──────────────────────────▼──────────────────────────┐
                    │              TURN CLOSED                             │
                    │  close_turn() called. Context ends with             │
                    │  synthetic user marker. Assistant message appended.  │
                    └─────────────────────────────────────────────────────┘
```

## Sentinel

- **Constant:** `ACCIDENTAL_EOT` = `"ENDOFTURN"` (assembled from `_ACCIDENTAL_EOT_PREFIX` at runtime)
- **Purpose:** LLM signals intent to end the turn
- **Detection:** Case-insensitive, exact match or suffix match (preceding content preserved)
- **Self-confirming:** Plain text ending with sentinel outside confirmation round → turn ends immediately
- **Confirmation round:** LLM replies with sentinel → `accept_confirmation()` closes turn

## Response Selection Priority

When `accept_confirmation()` resolves the final response text:

1. **`held_text`** — The LLM's substantive response shown in `<LASTREPLY>`. This is the answer being confirmed. Preferred unless malformed.
2. **`last_substantive_response`** — Fallback. May be stale from a previous turn. Used only when `held_text` is empty or malformed.
3. **`""` (empty)** — Last resort fallback.

**Rationale:** `held_text` is the current turn's answer. `last_substantive_response` can be stale if the current turn's response was held but not yet confirmed.

## Key Invariants

1. **Alternation:** Context always maintains `system → user ↔ assistant ↔ tool` order. EOT confirmation injects `assistant(held) → user(confirmation)` — valid alternation.
2. **Reset:** EOT state resets at start of each `run_loop()` via `agent._eot_protection.reset()`.
3. **Stack:** Confirmation stack holds messages across multiple rounds. Each `handle_potential_eot()` pushes one layer (assistant + synthetic user).
4. **Pop:** `pop_all_confirmations()` removes all stacked layers. Uses best-effort role/content matching.
5. **Budget:** `_ACCIDENTAL_EOT_BUDGET = 20`. After 20 confirmation attempts, turn is force-closed.
6. **Restricted nesting:** T (think) and K (skill) nesting types bypass confirmation entirely.
7. **Sentinel assembly:** Sentinel string assembled from parts to prevent LLM pattern learning.
8. **No recovery:** Context validation errors MUST be fixed at source. No recovery bridges.

## Entry Points

| Entry | Location | Description |
|-------|----------|-------------|
| `run_loop()` | `agent_loop.py:133` | Main loop. Resets EOT state. Handles all EOT paths. |
| `handle_potential_eot()` | `agent_eot_protection.py:200` | Hold message, inject confirmation request. |
| `check_confirmation()` | `agent_eot_protection.py:162` | Check response for sentinel. |
| `accept_confirmation()` | `agent_eot_protection.py:444` | Accept EOT, close turn. |
| `rewind_with_tools()` | `agent_eot_protection.py:391` | Rewind from confirmation, process tool calls. |
| `pop_all_confirmations()` | `agent_eot_protection.py:314` | Remove all confirmation layers. |
| `pop_synthetic_only()` | `agent_eot_protection.py:368` | Remove synthetic confirmations only (for slash commands). |
| `reset()` | `agent_eot_protection.py:143` | Reset EOT state. Called at turn start and on error. |

## Pre-Flight Size Check

Before injecting a confirmation request, `handle_potential_eot()` estimates whether
the resulting context would exceed 85% of `max_context_tokens`. If so, the
confirmation is skipped and the turn is force-closed with the held text.

**Formula:** `confirmation_tokens = len(synthetic_content) // 3 + 15`
**Threshold:** `max_context_tokens * 0.85`

## Error Handling

- **LLM call failure after confirmation injected:** `reset()` pops leftover confirmations.
- **Context corruption:** `pop_all_confirmations()` uses best-effort matching, stops on mismatch.
- **Budget exhaustion:** Turn force-closed with `last_substantive_response` or current response.

## Audit Events

| Event | When |
|-------|------|
| `EOT_CONFIRM_REQUEST` | Confirmation request injected |
| `EOT_CONFIRM_SKIPPED` | Pre-flight size check skipped confirmation |
| `EOT_CONFIRM_SENTINEL` | LLM replied with sentinel |
| `EOT_SELF_CONFIRMED` | Self-confirming ENDOFTURN detected |
| `EOT_CONFIRM_ACCEPTED` | Confirmation accepted, turn closed |

## `_resolve_end_turn_message()` Sentinel Rejection

When the LLM calls `end_turn(message="...")` during a confirmation round, the
message is rejected if it is essentially just the ENDOFTURN sentinel (≤13 chars
containing the sentinel, case-insensitive). This prevents the LLM from
overwriting a held substantive response with `end_turn(message="ENDOFTURN")`.

**Fallback chain:** held text → `last_substantive_response` → `"[end_turn — no message]"`
