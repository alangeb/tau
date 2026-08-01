---
name: tool_template
description: Create agent tools — dataclass Args, run() function, ToolMetadata. Create tool, tool format, new tool, tool definition, custom tool (also load: command_template, skill_template, caveman)
category: development
keywords: tool, create tool, tool format, tool definition, custom tool, dataclass, run function
---

# Tool Template

## When
"create tool", "tool format", "new tool", "tool template", "write tool"

## Mandatory
- **No module docstring** — `name` + `description` serve as docs
- **dataclass required** — `@dataclass` for Args
- **Complete Args** — all fields with precise types + descriptions
- **No `main()`** — tools are library modules
- **`_ctx: ToolContext`** — MANDATORY for ALL tools, last param, `= None` default

## Structure
```python
from __future__ import annotations

from tools import ToolContext, ToolMetadata
from dataclasses import dataclass, field

metadata = ToolMetadata(
    name="tool_name",
    description="Tool description in markdown.",
    aliases_cmd=["alt_name"],         # Optional
    aliases_arg={"p": "path"},        # Optional
    max_size=16384,                   # Optional, default 16384
    timeout=180,                      # Optional, default 180s
)

@dataclass
class Args:
    arg1: str = field(description="Description")
    arg2: int = field(default=0, description="Description")

def run(arg1: str = "", arg2: int = 0, _ctx: ToolContext | None = None) -> str:
    agent = _ctx.agent if _ctx else None
    tool_call_id = _ctx.tool_call_id if _ctx else None
    return "result"
```

## Metadata
| Variable | Type | Default | Purpose |
|----------|------|---------|---------|
| `name` | `str` | — | **Mandatory.** Canonical tool name |
| `description` | `str` | — | **Mandatory.** Markdown for LLM |
| `timeout` | `int` | `180` | Seconds. Long-running (fork, subagent) = `86400` |
| `aliases_cmd` | `list[str]` | `[]` | Alternative names, resolved silently |
| `aliases_arg` | `dict[str, str]` | `{}` | Alt param names → canonical, resolved silently |
| `max_size` | `int` | `16384` | Output truncation threshold (bytes) |

## Common Pitfalls
| Pitfall | Fix |
|---------|-----|
| Passing `wait` to `ls` as `all_sessions` | Separate params in `run()` |
| `scrollback=0` expects history | Use `≥30` |
| Confusing `send_keys` with `exec` | `send_keys` = input, `exec` = execute |
| Forgetting `_ctx` param | Always include `_ctx: ToolContext | None = None` |
| Using Pydantic instead of dataclass | Use `@dataclass` + `field()` |

## Helper
```bash
python3 skills/tool_template/tool_gen.py
```

## Related Skills
- `command_template` — creating commands (sibling concept)
- `skill_template` — creating skills (sibling concept)
- `caveman` — concise writing style
