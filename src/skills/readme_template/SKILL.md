---
category: documentation
description: "Generate README template with standard sections: overview, concepts, architecture, testing, development (also load: _taudoc, caveman, documentation, skill_template)"
keywords: readme template, README structure, documentation sections, project overview, architecture docs, development docs, readme writing
name: readme_template
---

# README.md Structure

## When
"write readme" | "readme structure" | "document project" | "update readme" | "readme template" | "readme" | "documentation" | "doc" | "write file" | "write a script"

## Tau README Sections (in order)
1. **Table of Contents** — Links to all major sections
2. **Overview** — What it is, key features, goals
3. **Core Concepts** — Architecture principles, design decisions
4. **Command System** — Built-in commands, custom commands, placeholders
5. **Tool Ecosystem** — File ops, process mgmt, AI/Research, self-mgmt, subagents, schema gen
6. **Testing** — Suite overview, coverage, running instructions
7. **Development** — Code style, adding tools/commands/skills
8. **Architecture** — Component descriptions, design decisions
9. **Design Decisions** — Specific choices, trade-offs
10. **Advanced Topics** — Special features, edge cases, performance

## Rules
- Status quo only — no history, migration guides, dates, deprecated features
- Use `pyscan` + `pyanalyze` for accurate code info
- Update TOC when sections change
- Consistent formatting, clear examples, actionable content

## Helper
```bash
python3 skills/readme_template/readme_gen.py  # readme_template helper
```

## Related Skills
- `command_template` — Document commands in README
- `project-onboard` — Gather project info for README
- `skill_template` — Document skills in README
- `documentation` — docstring and changelog patterns
- `_taudoc` — Tau documentation structure and style
- `caveman` — concise writing style for README
