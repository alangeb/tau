# Tools — Implementation Guide

**See also**: [ARCHITECTURE.md](ARCHITECTURE.md) (module inventory), [EOT.md](EOT.md) (end_turn tool), [INDEX.md](INDEX.md) (design index)

## Tool Contract

Every tool is a Python module in `tools/` with:

```python
from tools import ToolMetadata
from dataclasses import dataclass

metadata = ToolMetadata(
    name="tool_name",
    description="What it does",
    # Optional:
    aliases_cmd=["alias1"],
    aliases_arg={"old": "new"},
    max_size=10000,  # Output truncation threshold
    timeout=180,     # Execution timeout (seconds)
)

@dataclass
class Args:
    """Tool arguments — auto-converted to JSON Schema."""
    param: str

def run(param: str = "", _ctx: ToolContext | None = None) -> str:
    """Execute tool. Return string result."""
    agent = _ctx.agent if _ctx else None
    tool_call_id = _ctx.tool_call_id if _ctx else None
    ...
```

## Key Rules

1. **Auto-discovered** via `tools/__init__.py` — no manual registration needed.
2. **`_ctx: ToolContext` is the single context parameter** — provides access to `agent` and `tool_call_id`.
3. **User-facing params FIRST** (with defaults), **`_ctx` LAST** — consistent schema for LLM.
4. **Use `tools/validation.py`** for `_dataclass_to_json_schema()` to generate JSON Schema.
5. **Use `tools/lib/sandbox.py`** for path validation (`check_path`, `validate_path`) — enforces working directory boundaries.
6. **No `main()` functions** — tools are not standalone scripts.
7. **See `tool_template` skill** for the full template and examples.

## Common Patterns

```python
def run(param: str = "", _ctx: ToolContext | None = None) -> str:
    agent = _ctx.agent if _ctx else None
    tool_call_id = _ctx.tool_call_id if _ctx else None
    # Use sandbox validation for file paths
    from tools.lib.sandbox import check_path
    resolved, err = check_path("my_tool", agent, filepath)
    if err:
        return err
    # Do work...
    return result
```

**Key rules**: User params FIRST (with defaults), `_ctx: ToolContext | None = None` LAST. Access agent via `_ctx.agent`. Use `tools/lib/sandbox.py` for path validation. No `main()` functions.

## Tool Implementation Rules

| Rule | Details |
|------|---------|
| Location | Python modules in `tools/` directory |
| Mandatory | `metadata: ToolMetadata` at module level (replaces old `name`/`description` variables) |
| Args | `Args` dataclass with complete type definitions |
| Signature | `run(**kwargs) -> str` matching Args model |
| Optional | `aliases_cmd`, `aliases_arg`, `max_size`, `timeout` in `ToolMetadata` |
| Discovery | Auto-discovered via `tools/__init__.py` |
| Errors | Return error strings — never escape exceptions |
| Sandbox | Use `tools/lib/sandbox.py` for all file paths |
| Bash | `DANGEROUS_PATTERNS` are LLM nudges only — bash = trust boundary, real security is environmental (see DECISIONS.md §29) |
| Fetch | Redirect limit: 10, response size limit: 50MB, Crawl4AI curl uses `shlex.quote()` for injection prevention |
| Sandbox Cache | `clear_sandbox_cache()` available for manual cache invalidation when config changes |

## Tool-Specific Notes

### bash (`tools/bash.py`)

- Executes via `subprocess.run(cmd, shell=True)` — full shell access
- `DANGEROUS_PATTERNS` (16 regex patterns) serve as LLM nudges, NOT security gates
- Double-call confirmation for dangerous commands (rejected first time, allowed on repeat)
- **Security philosophy**: Once bash is available, no code-level sandbox can contain the agent. Real security = environmental isolation (containers, VMs). See **DECISIONS.md §29**.

### fetch (`tools/fetch.py`)

- Crawl4AI first-attempt with native HTML-to-markdown fallback
- **Redirect limit**: 10 (via `_LimitedRedirectHandler`)
- **Response size limit**: 50MB (via `_read_with_limit()` with 64KB chunks)
- **Crawl4AI injection prevention**: `shlex.quote()` used on all curl payloads
- URL cache: 1-hour TTL via `FileCache`

### sandbox (`tools/lib/sandbox.py`)

- `check_path()` — resolve + sandbox check + double-call confirmation (for write tools)
- `validate_path()` — resolve + sandbox check only (for read tools)
- `get_allowed_paths()` — extract whitelist from agent config
- `clear_sandbox_cache()` — clear resolved whitelist cache (call when config changes)
- Whitelist: reads from whitelisted paths bypass double-call; writes ALWAYS require double-call

### end_turn (`tools/end_turn.py`)

- Signals end of turn; sets `force_end_turn` on agent
- Resolves empty message to `last_substantive_response`
- Must be sole tool call in message; if mixed with other tools, silently filtered out
- See **EOT.md** for full end-of-turn contract (confirmation flow, sentinel, invariants)

## Why This Design?

Tools are dynamically discovered to avoid registration overhead. The `Args` dataclass pattern gives us auto-generated JSON Schema for LLM function calling. Sandbox validation prevents the agent from escaping the working directory.
