---
name: tauskillmaintenance
description: "Periodic skill maintenance — 10-phase audit, cross-reference check, gap analysis, helper file audit, usage tracking, health dashboard (also load: skill_template, caveman, tau_audit, dream, tool_template, code-review-workflow)"
category: maintenance
keywords: skill maintenance, skill audit, skill quality, skill review, periodic maintenance, findability, cross-reference, gap analysis, helper files, usage tracking, skill health, discovery, overlap
---

# Tau Skill Maintenance

## When
"skill audit", "maintain skills", "update skills", "skill maintenance", "review skills", "skill health", "skill gaps", "improve findability"

## 10-Phase Audit

### Phase 1: Audit Log Analysis
Parse `~/.local/tau/log/*_1.audit` for tool usage and skill load frequency.
```python
import glob, re, os; from collections import Counter
logs = glob.glob(os.path.expanduser("~/.local/tau/log/*_1.audit"))
tool_names, skill_names = [], []
for f in sorted(logs):
    text = open(f).read()
    tool_names.extend(re.findall(r"final_name='([^']*)", text))
    skill_names.extend(re.findall(r'"skill_name":\s*"([^"]*)', text))
for label, names in [("Tool Usage", tool_names), ("Skill Loads", skill_names)]:
    print(f"=== {label} ===")
    for name, count in Counter(names).most_common(30):
        print(f"  {count:5}  {name}")
```

### Phase 2: Skill Quality Audit
Verify: YAML frontmatter (name, description, category), `(also load: ...)` refs, search keywords, no tutorials, has "When"/"Related Skills"/"Helper" sections, under 120 lines, desc 30-200 chars. Rewrite using `caveman` style.

### Phase 3: Cross-References
Check bidirectionality — every `(also load: ref)` should have ref → skill back-reference.
Fix one-way refs or skip if intentionally directional.
**Trigger Keywords:** Verify each skill's description contains natural-language phrases users would search for.

### Phase 4: Missing Skills
1. Map high-frequency tools to skills (bash→shell_scripting, file_read→file-ops, etc.)
2. Find gaps — tools with 50+ calls but no skill coverage
3. Fix underloaded skills — add trigger keywords
4. Create skills for genuine gaps

### Phase 4.5: Skill Overlap Detection
1. Extract keyword sets from each skill's YAML frontmatter
2. Compute Jaccard similarity between all pairs
3. Flag pairs with >60% keyword overlap for review
4. Merge if overlap >80% and scope identical; split if scope diverges

### Phase 5: Helper File Audit
Check each skill for helper files (.py, .sh) — verify they exist and are referenced in SKILL.md.

### Phase 6: Usage Tracking
Track skill load frequency. Remove skills with 0 loads for 3+ months. Merge overlapping, split oversized (>120 lines).

### Phase 7: Description Quality
Verify 30-200 chars, no redundant keywords, natural-language triggers, no duplicate "also load:".

### Phase 8: Automation
Create `skills/tauskillmaintenance/run_audit.py` — runs all 10 phases, outputs markdown to `~/.local/tau/skill_audit.md`, exits non-zero on critical issues. Accepts `--phase N` and `--fix` flags. Cron-able.

### Phase 9: Skill Discovery
Analyze why skills aren't loaded: check description keywords vs common prompts, verify intuitive names, rate findability score (0-100), flag <50 for rewrite.

### Phase 10: Skill Health Dashboard
Generate summary: total skills, avg lines, avg desc length, cross-ref density, bidirectionality rate, helper coverage, usage distribution, description quality score.

## Tool-to-Skill Mapping
| Tool | Skill |
|------|-------|
| `bash` | `shell_scripting` |
| `grep` | `grep_tool` |
| `file_read/edit/write` | `file-ops` |
| `pyscan/pyanalyze/pygraph/pycheck` | `code-review-workflow` |
| `background_*` | `background` |
| `fork/subagent/background_run` | `delegation` |
| `subagent/fork` (prompt) | `prompt-crafting` |
| `fetch/search/lookup/crawl` | `web-research` |
| `see` | `image` |
| `plan/info/think/skill` | `plan_template/info/think/skill_template` |
| `ls/glob/head` | `file-ops` |

## Quick Commands
```bash
ls skills/*/SKILL.md | wc -l
for f in skills/*/SKILL.md; do lines=$(wc -l < "$f"); [ "$lines" -gt 120 ] && echo "$f: $lines lines"; done
```

## Rules
1. **Every tool needs a skill** — 5+ uses → create skill
2. **Descriptions must be findable** — include natural-language trigger phrases
3. **Cross-references must be bidirectional** — fix one-way refs
4. **Helper files must exist** — verify .py/.sh match SKILL.md references
5. **Skills must be concise** — under 120 lines, no tutorials
6. **Track usage** — monitor load frequency, remove dead skills
7. **Audit regularly** — run 10-phase audit monthly
8. **Descriptions 30-200 chars** — no too short, no too long
9. **Cross-ref bidirectionality** — aim for <10 one-way refs
10. **Map new tools immediately** — don't wait
11. **Add trigger keywords to underloaded skills**
12. **Use `caveman` style for all skill content**
13. **Skills must be discoverable** — test descriptions against sample prompts
14. **Monitor skill load rate** — target >30% of sessions load ≥1 skill
15. **Review overlap quarterly** — merge or differentiate similar skills

## Helper Script
```bash
python3 skills/tauskillmaintenance/skill_audit.py          # Full audit
python3 skills/tauskillmaintenance/skill_audit.py --health  # Health dashboard
python3 skills/tauskillmaintenance/skill_audit.py --discover # Discovery analysis
python3 skills/tauskillmaintenance/skill_audit.py --overlap  # Overlap detection
python3 skills/tauskillmaintenance/skill_audit.py --phase N  # Single phase
python3 skills/tauskillmaintenance/skill_audit.py --fix      # Auto-fix simple issues
```
`skill_audit.py` runs all 10 phases. Outputs to `~/.local/tau/skill_audit.md`. Checks: frontmatter, description length, cross-reference bidirectionality, helper file existence, usage frequency, keyword overlap, gap analysis, discovery scoring, and health dashboard. Exits non-zero on critical issues.

## Related Skills
- `caveman` — concise writing style
- `code-review-workflow` — automated code analysis
- `dream` — self-improvement orchestrator
- `skill_template` — format for new skills
- `tau_audit` — analyze agent logs
- `tool_template` — sibling concept for tools
