---
name: tauskillmaintenance
description: Periodic skill maintenance — 5-phase audit, cross-reference check, gap analysis, helper file verification, usage pattern analysis. Skill maintenance, skill audit, skill update, skill gaps, skill health, improve skills, findability, cross-references (also load: skill_template, command_template, caveman, tau_audit, dream, tool_template)
category: maintenance
keywords: skill maintenance, skill audit, skill quality, skill review, periodic maintenance
---

# Tau Skill Maintenance

## When
"skill audit", "maintain skills", "update skills", "skill maintenance", "review skills", "skill health", "skill usage", "skill gaps", "improve findability", "cross-reference check"

## 5-Phase Audit

### Phase 1: Audit Log Analysis
```bash
# Tool usage across all logs
for f in ~/.local/tau/log/*_2026*_1.audit; do
  grep -oP "final_name='[^']*" "$f" | sed "s/final_name='"//
done | sort | uniq -c | sort -rn

# Skill loading frequency
grep -rh '"skill_name":\s*"[^"]*"' ~/.local/tau/log/*_2026*_1.audit | \
  grep -oP '"skill_name":\s*"\K[^"]+' | sort | uniq -c | sort -rn
```

### Phase 2: Skill Quality Audit
For EACH skill, verify:
- [ ] YAML frontmatter: `name`, `description`, `category`
- [ ] Description includes `(also load: skill_template, command_template, caveman, tau_audit, dream, tool_template)`
- [ ] Description has search-trigger keywords
- [ ] Concise — no tutorials, no obvious content
- [ ] Has "When" section with trigger keywords
- [ ] Has "Related Skills" section
- [ ] Under 120 lines

Rewrite using `caveman` style: drop articles, remove fillers, fragments OK.

### Phase 3: Findability & Cross-References
```python
# Check bidirectionality (handle files without trailing newline)
import os, re
skills = {d: open(os.path.join("skills", d, "SKILL.md")).read()
          for d in os.listdir("skills")
          if os.path.exists(os.path.join("skills", d, "SKILL.md"))}
existing = set(skills.keys())
for name, content in skills.items():
    m = re.search(r'\(also load:\s*(.+?)\)', content)
    if m:
        refs = [r.strip() for r in m.group(1).split(',')]
        for ref in refs:
            if ref in existing and name not in skills.get(ref, ''):
                print(f"ONE-WAY: {name} -> {ref}")
```
Fix one-way refs: add back-reference OR skip if intentionally directional.

### Phase 4: Identify Missing Skills
1. Map high-frequency tools to existing skills
2. Find gaps — tools with 50+ calls but no skill coverage
3. Fix underloaded skills — high tool usage but <5 skill loads (fix keywords)
4. Create skills for genuine gaps
5. Improve descriptions for underloaded skills

### Phase 5: Helper File Audit
1. Check each skill for helper files (.py, .sh)
2. Verify helpers work (syntax check)
3. Consolidate redundant helpers
4. Create helpers for skills that would benefit

## Helper Script
```bash
python3 skills/tauskillmaintenance/skill_audit.py  # Full audit
```

## Continuous Improvement
- Run audit monthly or after major skill changes
- Track skill load frequency over time
- Remove skills with 0 loads for 3+ months
- Merge overlapping skills
- Split oversized skills (>120 lines)

## Related Skills
- `skill_template` — format and structure for new skills
- `command_template` — sibling concept for commands
- `tool_template` — sibling concept for tools
- `caveman` — concise writing style for skills
- `tau_audit` — analyze agent logs for behavior patterns
- `dream` — self-improvement orchestrator
