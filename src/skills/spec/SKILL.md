---
description: "Write specification with acceptance criteria, implement from spec — create specs/active/, validate requirements, ADR documentation (also load: plan_template, task, documentation, release_management)"
keywords: spec-driven development, design specification, acceptance criteria, spec writing, implement from spec, specification, architecture, system design, ADR, architecture decision record, design pattern, component diagram, system architecture, technical design
name: spec
category: planning
---

# Spec-Driven Development

## When
"spec-driven" | "spec workflow" | "write spec" | "implement from spec" | "code review" | "review code" | "architecture" | "system design" | "ADR" | "design decision" | "component diagram" | "technical design"

## Skip Specs When
Single-prompt tasks, throwaway prototypes, mechanical changes, obvious bug fixes. Write spec when: multi-session, expensive to reverse, needs review.

## Directory Structure
```
specs/
├── INDEX.md
├── ARCHITECTURE.md                   # Cross-cutting decisions (only when affects 2+ specs)
├── active/                           # WIP specs
│   └── YYYY-MM-DD-name.md
└── completed/                        # Frozen historical records
    └── YYYY-MM-DD-name.md
```
Lifecycle: `active/` → `completed/` (done) or `rm` (abandoned, git preserves).

## Workflow
0. **DECIDE** — Skip if trivial. Write spec if multi-session or expensive to reverse.
0.5. **RESUME** — `ls specs/active/` — find partial `[x]` → continue from first `[ ]`.
1. **DISCOVER** — `cat specs/INDEX.md`; `grep -rl "area: <keyword>" specs/`; read 1-3 relevant specs; if `depends:` not in `completed/`, complete dependency first.
2. **WRITE SPEC** — Create `specs/active/YYYY-MM-DD-name.md`. Edit IN PLACE during implementation.
3. **REVIEW** — `python3 skills/spec/validate_spec.py <file>`. Fix every FAIL. Address WARNs. Rerun until PASS.
4. **IMPLEMENT** — For each criterion: implement → write tests → mark `[x]`. Commit after each `[x]`. STOP if spec needs updating → edit in place, commit, continue. No scope creep.
5. **VERIFY** — All criteria `[x]`. Run project test suite. No drift from spec. Load `review` skill.
6. **COMPLETE** — `mv specs/active/... specs/completed/`. Update INDEX.md. `git add specs/ <changed> && git commit -m "spec: <desc>"`.
7. **ABANDON** — `rm specs/active/...`. Remove from INDEX.md. `git add specs/INDEX.md && git rm specs/active/... && git commit -m "spec: abandoned <desc>"`.
8. **ITERATE** — New spec references completed via `depends:` (blocking) and `related:` (informative). Repeat from Phase 0.

## Spec File Format
```yaml
---
name: short-descriptive-name
status: active
area: auth, api
depends: spec1               # BLOCKING — must be in completed/ (or "none")
related: spec2, spec3        # INFORMATIVE — read for context (or "none")
---
# Short Descriptive Name
## Problem — One paragraph. What's broken?
## Solution — High-level approach.
## Non-Goals — What this spec WON'T do.
## Acceptance Criteria — - [ ] Given <precondition> When <action> Then <outcome>
## Files Affected — - `path/to/file.py` — what changes
## Edge Cases — Timeouts, permissions, duplicates, race conditions
## Rollback — How to undo if implementation fails.
```

## Tagging
`area:` field — lowercase, comma-separated. Reuse existing tags. Good: `auth`, `api`, `cli`, `config`. Bad: `stuff`, `misc`, `auth-system`.

## Review Checklist (enforced by validate_spec.py)
**FAIL:** Frontmatter (name, status, area, depends, related). Sections non-empty: Problem, Solution, Non-Goals, Acceptance Criteria, Files Affected, Edge Cases, Rollback. Criteria in `[ ]`/`[x]` format. ≤10 criteria, ≤5 files. `depends:` specs in `completed/`.
**WARN:** Criteria not matching `Given.*When.*Then`.

## Helper
```bash
python3 skills/spec/validate_spec.py <spec-file>
```

## ADR (Architecture Decision Record)

When a spec requires a cross-cutting design decision (affects 2+ specs), write an ADR in `designs/adr/`:

```markdown
---
title: "Short title"
status: proposed|accepted|deprecated|superseded
date: YYYY-MM-DD
---

## Context
What situation requires decision?

## Decision
What was decided?

## Consequences
What results from this decision?
- Positive:
- Negative:
- Neutral:
```

Use `graphify` skill to generate call graphs. Store diagrams in `designs/diagrams/`.

## Related Skills
- `git` — commit spec + implementation
- `plan_template` — task planning for spec implementation
- `review` — code review after implementation
- `graphify` — Visualize architecture with call graphs
- `release_management` — Version bumping, changelog, release notes
