---
name: skill_tool
description: "List and load skills by name — skill discovery, search, find (also load: skill-discovery, skill_template, command_template, tool_template, tauskillmaintenance, _taudoc, caveman)"
category: discovery
keywords: skill, skills, list skills, load skill, find skill, skill name, skill search, skill discovery
---

# Skill Tool

## When
"list skills", "load skill", "find skill", "skill name", "skill search"

## Usage
- `skill("")` — list all available skills
- `skill("name")` — load skill content by exact name
- `skill("name")` — case-insensitive/fuzzy match on no exact match

## Pattern
1. `skill("")` — list all skills
2. Search for relevant skill by name/keyword
3. `skill("name")` — load skill content
4. Use skill knowledge in current task
5. Cross-reference related skills

## Related Skills
- `_taudoc` — documentation structure
- `caveman` — concise writing style
- `command_template` — create custom command
- `skill_template` — create new skill
- `tauskillmaintenance` — skill maintenance
- `tool_template` — create agent tool
## Helper
```bash
python3 skills/skill_tool/skill_finder.py              # List all skills
python3 skills/skill_tool/skill_finder.py search <kw>  # Search skills by keyword
python3 skills/skill_tool/skill_finder.py get <name>   # Get skill content
```