---
name: skill_template
description: Create new skill or modify existing skills. Create skill, skill format, skill definition (also load: tool_template, command_template, tau_audit, tauskillmaintenance, _taudoc, caveman, readme_template, documentation, reference)
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
description: One-liner for search
category: category_name
keywords: create skill, skill format, skill definition, new skill, skill template, write skill
---
```
Missing header = skill fails to load.

## Placement
- `skills/` directory (sibling to `tools/`)
- `.md` extension only
- No leading underscore in filenames

## Rules
- Project-specific knowledge only — not general Python/CLI basics
- One topic per skill
- Concise — skip what the model already knows
- Include code examples

## Autonomy

**Tau is AUTHORIZED to create skills on its own.** Do NOT wait for user permission. When Tau identifies a repeated pattern, missing capability, or knowledge gap, create the skill immediately. This is a core self-improvement behavior.

## Privacy

**NO personal information in skills, source code, or any project file.** Never include:
- Real timestamps (use `YYYY-MM` or relative dates)
- User names, email addresses, personal paths
- Anything identifying outside the project

Use `$HOME` instead of `/home/alangeb`. The only acceptable personal reference is `alangeb` in the context of `$HOME` paths, and even that should be avoided where possible.

## Discovery
- Auto-discovered on startup. List via `skill`. Search via `skill <keywords>`. Load via `skill {"skill_name": "name"}`.
- Full content injected into context as tool result message when loaded.

## Helper

```bash
python3 skills/skill_template/skill_gen.py  # skill_template helper
```
## Related Skills
- `tool_template` — creating agent tools (sibling concept)
- `command_template` — creating commands (sibling concept)
- `tauskillmaintenance` — audit and maintain skills
- `caveman` — concise writing style
- `_taudoc` — documentation structure
- `tau_audit` — analyze agent behavior
- `dream` — self-improvement orchestrator
- `task_creation` — creating tasks for dream execution

- `reference` — Tau quick reference
- `readme_template` — README structure