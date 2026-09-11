---
description: "Update docs, maintain design docs, TAU.md, AGENT.md, designs/ — verify cross-links, sync docs with code (also load: documentation, caveman, readme_template, skill_tool, task)"
keywords: tau documentation, design docs, TAU.md, AGENT.md, documentation layout, doc maintenance, architecture docs, doc update, project docs
name: _taudoc
category: documentation
---

# Tau Documentation Layout

## When
"update docs", "documentation structure", "designs folder", "TAU.md", "AGENT.md", "documentation maintenance"

## Structure (relative to `src/`)
```
src/
├── AGENT.md              ← System prompt → TAU.md
├── TAU.md                ← Dev index → designs/
├── README.md             ← Minimal pointer
└── designs/
    ├── INDEX.md          ← Navigation
    ├── ARCHITECTURE.md   ← Request flow, modules, patterns
    ├── DECISIONS.md      ← Design decisions (232, 27 categories)
    ├── CONTEXT.md        ← Context management
    ├── COMMANDS.md       ← Command implementation
    ├── SKILLS.md         ← Skill implementation
    ├── TESTING.md        ← Testing guide
    └── TOOLS.md          ← Tool implementation
```

## Rules
1. **AGENT.md** — System prompt. NEVER modify except TAU.md reference.
2. **TAU.md** — Dev index → designs/.
3. **designs/** — ALL design docs. None outside.
4. **README.md** — Minimal pointer only.
5. **commands/_taudoc.md** — Doc maintenance command only.
6. **skills/_taudoc/** — Doc maintenance skill only.
7. All paths RELATIVE to `src/`.
8. NEVER create docs outside `designs/` without approval.
9. NEVER remove `designs/DECISIONS.md` entries — manual only.
10. ALWAYS verify cross-links before committing.

## Workflow
1. Read `TAU.md` + relevant `designs/*.md`
2. `pyscan` + `pyanalyze` on `src/`
3. Code vs docs → update docs → remove overlaps
4. Verify cross-links → commit

## Helper
```bash
python3 skills/_taudoc/doc_validator.py <src_path>  # Validate doc structure
```

## Related Skills
- `command_template` — Command creation format
- `documentation` — Docstring and changelog patterns
- `skill_template` — Skill creation format
- `tau_audit` — Analyze agent logs
- `dream` — Dream orchestrator
- `task` — Task framework
