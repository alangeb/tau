---
name: skill_template
description: "Create and modify skills — format, structure, helper. Skill definition, skill file, SKILL.md, skill creation, skill format (also load: tool_template, command_template, caveman, _taudoc, readme_template, documentation)"
category: development
keywords: create skill, skill format, skill definition, new skill, skill template, write skill
---

# Skill Format

## When
"create skill", "skill format", "new skill", "skill template", "write skill"

## Required Frontmatter
```yaml
---
name: skill_name
description: "Brief description (also load: related_skill1, related_skill2)"
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
**Tau is AUTHORIZED to create skills autonomously.** Repeated pattern, missing capability, or knowledge gap → create skill immediately. Core self-improvement behavior.

## Privacy
**NO personal info in skills, source code, or any project file.** Never include:
- Real timestamps (use `YYYY-MM` or relative dates)
- User names, email addresses, personal paths
- Anything identifying outside the project

Use `$HOME` instead of `/home/alangeb`.

## Discovery
- Auto-discovered on startup. List via `skill`. Search via `skill <keywords>`. Load via `skill <name>`.
- Full content injected into context as tool result message when loaded.

## Helper
```bash
python3 skills/skill_template/skill_gen.py <name> <description> <category>  # Generate skill template
```

## Related Skills
- `_taudoc` — documentation structure
- `caveman` — concise writing style
- `command_template` — creating commands (sibling concept)
- `readme_template` — README structure
- `tool_template` — creating agent tools (sibling concept)
- `documentation` — docstring and changelog patterns
