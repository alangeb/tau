---
name: _taudoc
description: Maintain TauErgon documentation structure — designs/, TAU.md, AGENT.md. Documentation structure, tau docs, design documents (also load: tau_audit, skill_template, documentation, command_template, dream)
category: maintenance
keywords: documentation, doc structure, tau docs, design documents, technical writing
---

# Tau Documentation Layout

## When
"update docs", "documentation structure", "designs folder", "TAU.md", "AGENT.md", "documentation maintenance"

## Structure (relative to `src/`)
```
src/
├── AGENT.md              ← System prompt. Points to TAU.md.
├── TAU.md                ← Developer index. Points to designs/.
├── README.md             ← Minimal pointer to TAU.md + designs/
└── designs/
    ├── INDEX.md          ← Navigation
    ├── ARCHITECTURE.md   ← Request flow, modules, patterns
    ├── DECISIONS.md      ← Design decisions (166+, 20 categories)
    ├── CONTEXT.md        ← Context management patterns
    ├── COMMANDS.md       ← Command implementation
    ├── SKILLS.md         ← Skill implementation
    ├── TESTING.md        ← Testing guide
    └── TOOLS.md          ← Tool implementation
```

## Rules
1. **AGENT.md** — System prompt. NEVER modify except TAU.md reference line.
2. **TAU.md** — Developer index. Points to designs/.
3. **designs/** — ALL design docs. None outside.
4. **README.md** — Minimal pointer. No content here.
5. **commands/_taudoc.md** — ONLY doc maintenance command.
6. **skills/_taudoc/** — ONLY doc maintenance skill.
7. All paths RELATIVE to `src/`.
8. NEVER create docs outside `designs/` without approval.
9. NEVER remove `designs/DECISIONS.md` entries — manual only.
10. ALWAYS verify cross-links before committing.

## Workflow
1. Read `TAU.md` + relevant `designs/*.md`
2. `pyscan` + `pyanalyze` on `src/`
3. Compare code vs docs
4. Update docs to match code
5. Remove overlaps
6. Verify cross-links
7. Commit

## Helper
```bash
python3 skills/_taudoc/doc_validator.py  # _taudoc helper
```

## Related Skills
- `tau_audit` — analyze agent logs
- `skill_template` — skill creation format
- `command_template` — command creation format
- `documentation` — docstring and changelog patterns
- `task` — task framework

- `dream` — Dream orchestrator