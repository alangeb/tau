---
category: development
description: "Create custom commands, command templates, markdown prompt templates, Python run functions (also load: skill_template, tool_template, shell_scripting, reference, skill_tool)"
keywords: custom prompt templates, markdown prompt format, Python run function, placeholder substitution, prompt aliasing
name: command_template
---

# command_template

## When
"create command" | "new command" | "command template" | "write command" | "write a script" | "bash command" | "write file" | "shell script"

## Markdown Format
```markdown
---
description: "Description (also load: skill_template, tool_template, shell_scripting, reference, skill_tool)"
---
Content with $1, $2, $* placeholders.
---
Second prompt (multi-prompt via ---)
```

### Placeholders
| Placeholder | Meaning |
|-------------|---------|
| `$1` | First arg |
| `$2` | Second arg |
| `$*` | All args |
| `$1+` | From $1 to end |

Content starting with `/` chains: `/fork Critique $1`

## Python Format
```python
name = "command_name"
description = "Brief description"
aliases_cmd = ["alias1"]  # Optional
aliases_arg = {"file": ["f", "path"]}  # Optional

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

## Choice
- **Markdown**: Simple prompts, multi-step sequences
- **Python**: Complex logic, tools, context manipulation, subagents

## Helper
```bash
python3 skills/command_template/command_gen.py
```

## Related Skills
- `skill_tool` — list and load skills
- `caveman` — Concise writing
- `_taudoc` — Documentation structure
- `readme_template` — README structure
- `reference` — Tau quick reference
- `shell_scripting` — Shell-based commands
- `skill_template` — Creating skills
- `tool_template` — Creating tools
