---
name: command_template
description: Create custom commands — markdown prompt templates and Python run() functions. Create command, command format, slash command, custom command, /command (also load: skill_template, tool_template, caveman, _taudoc)
category: development
keywords: command, create command, slash command, custom command, prompt template, run function
---

# Command Template

## When
"create command", "command format", "new command", "command template", "write command", "slash command"

## Two Types
- **Markdown (.md)**: Prompt templates with `$1`, `$2`, `$*` placeholders
- **Python (.py)**: Full agent access via `run(agent, args)`

## Markdown Format
```markdown
---
description: Brief description
---
Content with $1, $2, $* placeholders.
---
Second prompt (multi-prompt via ---)
```

### Placeholders
| Placeholder | Meaning |
|-------------|---------|
| `$1` | First argument |
| `$2` | Second argument |
| `$*` | All arguments |
| `$1+` | From $1 to end |

### Chaining
Content starting with `/` triggers another command: `/fork Critique $1`

### Writing Rules
1. **Assume agent knows basics** — no git/Python/shell explanations
2. **Lead with "NEVER"** — safety rules first
3. **FACTS table** — project-specific info only
4. **Procedures concise** — commands, not tutorials
5. **Define ERROR/WARNING** — error reporting up front
6. **Remove redundancy** — every line must carry unique info

## Python Format
```python
name = "command_name"
description = "Brief description"

def run(agent, args):
    """Args: agent=TauErgon, args=List[str]"""
```

### Agent Methods
```python
agent.context.get_messages()
agent.context.append_user("msg")
agent.context.clear()
result = agent._exec_tool("bash cmd='ls'")
tools = agent.get_all_tools()
response = agent.invoke_with_tools("Prompt")
agent.console.status("Working...")
agent.console.error("Error!")
agent.console.warning("Warning")
agent.console.echo("Text")
```

### Optional
```python
aliases_cmd = ["alias1"]
aliases_arg = {"file": ["f", "path"]}
```

## When to Use Which
- **Markdown**: Simple prompts, multi-step sequences
- **Python**: Complex logic, tools, context manipulation, subagents

## Helper
```bash
python3 skills/command_template/command_gen.py  # command_template helper
```

## Related Skills
- `skill_template` — creating skills (sibling concept)
- `tool_template` — creating tools (sibling concept)
- `_taudoc` — documentation structure
- `caveman` — writing concise commands
- `shell_scripting` — shell-based commands
- `reference` — quick reference for common commands
- `tauskillmaintenance` — audit command quality
- `readme_template` — README structure