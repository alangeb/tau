---
category: maintenance
description: "Maintain skills — audit quality, cross-refs, gaps, helpers, health dashboard, skill maintenance (also load: skill_template, tau_audit, caveman, skill-discovery, skill_tool)"
keywords: skill quality verification, cross-reference bidirectionality check, keyword overlap detection, helper file audit, findability scoring, skill load rate optimization, skill gap analysis, skill health dashboard
name: tauskillmaintenance
---

# Skill Maintenance

## When
"skill audit" | "maintain skills" | "update skills" | "skill maintenance" | "review skills" | "skill health" | "skill gaps" | "improve findability" | "skill sync" | "merge skills" | "trim skills"

## Audit Phases (8)

### Phase 1: Audit Log Analysis
Parse `~/.local/tau/log/*_1.audit`. Track: tool call counts, skill load rate (%), discovery gaps.

### Phase 2: Skill Quality Audit
Verify: YAML frontmatter (name, description, category), `(also load: ...)` refs, keywords, no tutorials, "When"/"Related Skills"/"Helper" sections, <80 lines, desc 30-200 chars. Rewrite caveman style. Keywords: 8-15 domain-specific. NEVER generic words (analysis, background, bash, code, command, configure, debug, delegate, edit, error).

### Phase 3: Cross-References
Check bidirectionality — every `(also load: ...)` needs back-ref. Fix one-way refs. Verify no missing targets.

### Phase 4: Missing Skills + Overlap
Map high-freq tools to skills. Gaps: tools 50+ calls, no skill. Jaccard similarity on keyword sets. >60% → merge review; >80% → merge.

### Phase 5: Helper File Audit
Check each skill for helpers (.py, .sh). Verify exist + referenced in SKILL.md. Fix orphans, expand stubs, remove dead code.

### Phase 6: Usage + Discovery + Health
Load rate target: >1%. If <1%, rewrite desc natural language. Remove 0-load skills 3+ months. Findability (0-100): desc 30-200 chars=+25, keywords 5-15=+25, cross-refs 3-10=+20, helper exists=+10, bidirectional refs 100%=+20. <50→REWRITE, <30→CRITICAL.

### Phase 7: Skill Sync
Sync skills/ ↔ ~/.local/tau/skills/. Verify identical. Remove stale.

### Phase 8: New Skill Creation
Map tool sequences to skills. Verify: frontmatter, When section, 5+ keywords, helper file, cross-refs, <80 lines.

## Skill Load Rate — Root Cause Analysis

### Current State (CRITICAL)
- Load rate: 0.02% (6 skill calls / 50 sessions / ~8000 tool calls)
- 66/69 skills NEVER loaded across last 50 sessions
- Only `background`, `spec`, `wiki` loaded (2 times each)
- Target: >1% (need 50+ skill calls per 50 sessions)

### Root Causes
1. **Agents don't know skills exist** — no skill index in system prompt
2. **No auto-suggest** — agents must guess skill names
3. **Skill() requires exact name** — fuzzy matching exists but agents don't try
4. **bash dominates 62%** — agents default to shell commands over skills
5. **Descriptions too technical** — don't match natural user prompts

### Fix Strategies (Priority Order)

#### 1. Inject Skill Index into AGENT.md (HIGH IMPACT)
Add top-10 skills section to AGENT.md with trigger phrases:
```
## QUICK SKILL REFERENCE
- `skill('debug')` — Python errors, tracebacks, pdb
- `skill('pyprep')` — Python project analysis, pyscan, pygraph
- `skill('background')` — Run tasks async in tmux
- `skill('delegation')` — subagent, fork, delegate work
- `skill('git')` — git operations, worktree, branches
- `skill('web-research')` — fetch, search, lookup, crawl
- `skill('testing')` — pytest, fixtures, coverage
- `skill('file-ops')` — file_read, file_edit, file_write
- `skill('grep_tool')` — grep patterns, structured search
- `skill('shell_scripting')` — bash utilities, scripts
```

#### 2. Tool Sequence Auto-Suggest (MEDIUM IMPACT)
After 3+ tool calls, suggest relevant skill:
- 3+ `bash`+`grep` → suggest `grep_tool`
- `pyscan`+`pygraph` → suggest `pyprep`
- `subagent`/`fork` → suggest `delegation`
- `background_*` → suggest `background`
- `file_read`+`file_edit` → suggest `file-ops`
- `fetch`+`search` → suggest `web-research`

#### 3. Rewrite Descriptions for Discovery (MEDIUM IMPACT)
- Use natural language, not technical terms
- Include trigger phrases users actually type
- Keep 30-200 chars, action-oriented

#### 4. Merge Redundant Skills (LOW IMPACT, HIGH EFFORT)
- 69 skills → target 30-40 (reduce choice paralysis)
- Merge: git+git-advanced+git-verify+gitcrit → single `git`
- Merge: manifest+plan_template → single `manifest`
- Merge: skill_tool+skill-discovery+skill_template → single `skill`

#### 5. Weekly Automated Audits (MAINTENANCE)
- dream cycle runs skill maintenance automatically
- Track load rate trends, alert on drops
- Remove 0-load skills after 3+ months

## Tool-to-Skill Mapping
`bash`→`shell_scripting` | `grep`→`grep_tool` | `file_read/edit/write/ls/glob`→`file-ops` | `pyscan/pyanalyze/pygraph`→`pyprep` | `background_*`→`background` | `fork/subagent`→`delegation` | `fetch/search/lookup`→`web-research` | `see`→`image` | `manifest_*`→`manifest` | `skill`→`skill_tool` | `health`→`health` | `sum`→`sum` | `gitcrit`→`gitcrit` | `manifests`→`orchestrate` | `refactor`→`refactor` | `debug`→`debug` | `pytest`→`testing`

## Command-to-Skill Mapping
`/delegate`→`delegation` | `/orchestrate`→`orchestrate` | `/manifests`→`manifest` | `/health`→`health` | `/sum`→`sum` | `/gitcrit`→`gitcrit` | `/pyprep`→`pyprep`

## Health Score
score = desc_quality*0.2 + cross_ref*0.2 + helper_coverage*0.15 + usage_freq*0.25 + findability*0.2. Thresholds: 90-100=HEALTHY, 70-89=OK, 50-69=NEEDS WORK, <50=CRITICAL. Targets: desc 30-200 chars | lines <80 | cross-ref avg 6+/skill | bidirectionality 100% | helper coverage 100% | keyword overlap <60% Jaccard | load rate >1%.

## Helper Scripts
```bash
python3 skills/tauskillmaintenance/skill_audit.py [--health|--discover|--overlap|--score|--phase N|--fix|--fix-bidir|--fix-desc]
python3 skills/tauskillmaintenance/skill_crossref.py [--check|--verbose]
python3 skills/tauskillmaintenance/skill_overlap.py
python3 skills/tauskillmaintenance/skill_discover.py <query>
python3 skills/tauskillmaintenance/skill_loadrate.py [N]
python3 skills/tauskillmaintenance/skill_health.py [--brief|--verbose|--json]
python3 skills/tauskillmaintenance/tool_suggest.py <audit_file>|--recent N
python3 skill_finder.py <query> [top=N]  # Standalone (run from src/)
```

## Related Skills
- `background` — Background tmux sessions
- `caveman` — Concise writing style
- `skill-discovery` — Auto-discover skills
- `skill_template` — Format for new skills
- `skill_tool` — List and load skills
- `tau_audit` — Analyze agent logs
- `tool_template` — Sibling concept for tools
