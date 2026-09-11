---
category: development
description: "Create skill template with YAML frontmatter, markdown body, placement rules, auto-discovery config (also load: caveman, documentation, prompt-crafting, tool_template, command_template, readme_template, skill-discovery, skill_tool, task, tauskillmaintenance)"
keywords: skill template, YAML frontmatter, skill creation, skill format, skill placement, privacy constraints, skill auto-discovery
name: skill_template
---

# Skill Format

## When
"create skill", "skill format", "new skill", "skill template", "write skill"

## Required Frontmatter
```yaml
---
name: skill_name
description: "Brief description (also load: caveman, documentation, prompt-crafting, tool_template, command_template, readme_template, skill-discovery, skill_tool, task, tauskillmaintenance)"
category: category_name
keywords: keyword1, keyword2, keyword3
---
```
Missing header = skill fails to load.

## Placement
- `skills/` directory (sibling to `tools/`)
- `.md` extension only
- No leading underscore in filenames

## Rules
- Project-specific knowledge only — no general Python/CLI basics
- One topic per skill
- Concise — skip what the model already knows
- Include code examples
- Write in caveman style (load `caveman` skill)

## Autonomy
**Tau AUTHORIZED to create skills autonomously.** Repeated pattern, missing capability, or knowledge gap → create skill immediately. Core self-improvement behavior.

## Privacy
**NO personal info in skills, source code, or any project file.** Never include:
- Real timestamps (use `YYYY-MM` or relative dates)
- User names, email addresses, personal paths
- Anything identifying outside the project
Use `$HOME` instead of `/home/user`.

## Discovery
- Auto-discovered on startup. List via `skill`. Search via `skill <keywords>`. Load via `skill <name>`.
- Full content injected into context as tool result message when loaded.

## Helper
```bash
python3 skills/skill_template/skill_gen.py <name> <description> <category>
```

## Related Skills
- `skill_tool` — list and load skills
- `skill-discovery` — auto-discover relevant skills
- `_taudoc` — Documentation structure
- `caveman` — Concise writing style
- `command_template` — Creating commands (sibling concept)
- `readme_template` — README structure
- `tool_template` — Creating agent tools (sibling concept)
- `documentation` — Docstring and changelog patterns
- `dream` — Dream orchestrator
- `reference` — Tau quick reference
- `task` — Creating tasks for dream execution (redirect: see task)
- `task` — Task framework, lifecycle, verification
- `tauskillmaintenance` — Audit and maintain skills
