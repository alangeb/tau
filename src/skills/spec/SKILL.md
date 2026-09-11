---
name: spec
description: "Spec-driven development — write design specs, acceptance criteria, validate and implement. Structured workflow for multi-session features (also load: git, review, plan_template)"
category: workflow
keywords: spec, specs, design spec, design specs, specification, spec-driven, spec-driven development, spec workflow, write spec, write specs, implement from spec, acceptance criteria, feature spec, feature design, technical spec, technical specification, TDD, plan before code
---

# Spec-Driven Development

## When
"spec-driven", "spec workflow", "write spec", "implement from spec"

## Skip Specs When
Single-prompt tasks, throwaway prototypes, mechanical changes, obvious bug fixes.
Write spec when: multi-session work, expensive to reverse, needs real review.

## Structure
```
specs/
├── INDEX.md                          # Markdown table
├── ARCHITECTURE.md                   # Cross-cutting decisions (create only when affects 2+ specs)
├── active/                           # WIP specs
│   └── YYYY-MM-DD-name.md
└── completed/                        # Frozen historical records
    └── YYYY-MM-DD-name.md
```
Lifecycle: `active/` → `completed/` (done) or `rm` (abandoned, git preserves).

## Tagging (`area:` field)
Lowercase, comma-separated. Reuse existing tags. Good: `auth`, `api`, `cli`, `config`, `testing`, `docs`, `performance`. Bad: `stuff`, `misc`, `auth-system`.

## Discovery
```bash
cat specs/INDEX.md                                    # Overview
grep -rl "area:.*<keyword>" specs/active/ specs/completed/  # Find relevant specs
```
Read only 1-3 relevant specs. If `INDEX.md` missing, recreate from template below.

---

## Workflow

### Phase 0: DECIDE — Need a spec?
Skip if trivial. Write spec if multi-session or expensive to reverse.

### Phase 0.5: RESUME — Check interrupted work
```bash
ls specs/active/
```
Find specs with partial `[x]` → read → continue from first `[ ]`.

### Phase 1: DISCOVER — Find context
1. `cat specs/INDEX.md`
2. `grep -rl "area: <keyword>" specs/`
3. Read 1-3 relevant specs (check `depends:` and `related:`)
4. If `depends:` not in `completed/`, complete dependency first
5. If `related:` lists specs, read for context (non-blocking)

### Phase 2: WRITE SPEC — Create `specs/active/YYYY-MM-DD-name.md`
Use format below. Edit IN PLACE during implementation — git tracks changes.

### Phase 3: REVIEW — Validate (FAIL → revise, do NOT implement)
```bash
python3 skills/spec/validate_spec.py specs/active/YYYY-MM-DD-name.md
```
Fix every FAIL. Address WARNs where reasonable. Rerun until PASS.

### Phase 4: IMPLEMENT — Criterion-by-criterion
1. Read spec in full
2. For each acceptance criterion: implement → write tests → mark `[x]`
3. Commit after each `[x]`: `git add -A && git commit -m "spec: implement <criterion summary>"`
4. STOP if spec needs updating → edit in place, commit, continue
5. No scope creep — implement exactly what spec says

### Phase 5: VERIFY
- All criteria `[x]`
- Run project test suite: all pass
- No drift from spec (re-read, verify each criterion)
- Load `review` skill, run code review

### Phase 6: COMPLETE — Freeze
```bash
mv specs/active/YYYY-MM-DD-name.md specs/completed/
# Update specs/INDEX.md: status → completed
git add specs/ <changed-files>
git commit -m "spec: short description"
```

### Phase 7: ABANDON — Delete (alternative to COMPLETE)
```bash
# Remove line from specs/INDEX.md
rm specs/active/YYYY-MM-DD-name.md
git add specs/INDEX.md
git rm specs/active/YYYY-MM-DD-name.md
git commit -m "spec: abandoned short description"
```

### Phase 8: ITERATE — Next task builds on this
New spec references completed ones via `depends:` (blocking) and `related:` (informative). Repeat from Phase 0.

---

## Spec File Format

```yaml
---
name: short-descriptive-name
status: active
area: auth, api              # comma-separated tags
depends: spec1               # BLOCKING — must be in completed/ first (or "none")
related: spec2, spec3        # INFORMATIVE — read for context (or "none")
---

# Short Descriptive Name

## Problem
One paragraph. What's broken or missing?

## Solution
High-level approach.

## Non-Goals
What this spec WON'T do.

## Acceptance Criteria
- [ ] Given <precondition> When <action> Then <observable outcome>

## Files Affected
- `path/to/file.py` — add/modify + what changes

## Edge Cases
- Timeouts, permissions, duplicates, race conditions

## Rollback
How to undo if implementation fails.
```

---

## INDEX.md Format

Create on first use:
```markdown
# Spec Index

| Status    | Date   | Name | Area | Link |
|-----------|--------|------|------|------|
```

Complete: `| completed | 2025-01 | add-auth-endpoint | auth, api | [link](completed/2025-01-15-add-auth-endpoint.md) |`
Abandon: remove line entirely. One line per spec.

---

## ARCHITECTURE.md — Trigger and Format

**Trigger:** Create ONLY when decision affects 2+ specs.

Create on first use:
```markdown
# Architecture Decisions

<!-- Add decisions below when a choice affects 2+ specs -->
```

Decision format:
```markdown
## 1. Use SQLite, not PostgreSQL
**Date**: 2025-01
**Affects**: add-auth-endpoint, add-user-model
**Rationale**: Single-file, zero-config, sufficient for our scale. Can migrate later.
```

---

## Review Checklist (enforced by validate_spec.py)

**FAIL (must fix):**
- Frontmatter: name, status, area, depends, related
- Sections exist, non-empty: Problem, Solution, Non-Goals, Acceptance Criteria, Files Affected, Edge Cases, Rollback
- Acceptance criteria present (`[ ]` or `[x]` format)
- ≤10 acceptance criteria (split if more)
- ≤5 files affected (split if more)
- `depends:` specs exist in `specs/completed/`

**WARN (should address):**
- Acceptance criteria not matching `Given.*When.*Then` pattern

## Helper
```bash
python3 skills/spec/validate_spec.py <spec-file>  # Validate spec
```

## Related Skills
- `git` — commit spec + implementation
- `review` — code review after implementation
- `plan_template` — task planning for spec implementation
