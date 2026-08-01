---
description: Periodic skill maintenance — review audit logs, audit skills, update for findability, add missing skills
---

# Periodic Skill Maintenance

## Phase 1: Audit Log Analysis

### 1.0 Get Audit Files from Registry

```bash
# Get audit files from registry (includes archived sessions)
cd src && python3 -c "
from agent_session_registry import get_registry
registry = get_registry()
files = registry.get_audit_files(include_archived=True)
for f in files[:50]:  # Last 50 sessions
    print(f)
" > /tmp/skill_audit_files.txt

# Fallback: scan LOG_DIR directly if registry fails
if [ ! -s /tmp/skill_audit_files.txt ]; then
  LOG_DIR="$HOME/.local/tau/log"
  ls -t "$LOG_DIR"/*.audit 2>/dev/null | head -50 > /tmp/skill_audit_files.txt
fi

echo "Audit files to analyze: $(wc -l < /tmp/skill_audit_files.txt)"
```

### 1.1 Gather Tool Usage Data
```bash
# Count tool invocations across all recent logs (portable grep, no -P flag)
while IFS= read -r audit_file; do
  [ -z "$audit_file" ] && continue
  [ -f "$audit_file" ] || continue
  grep -oE "final_name='[^']*" "$audit_file" 2>/dev/null | sed "s/final_name='"//
done < /tmp/skill_audit_files.txt | sort | uniq -c | sort -rn > /tmp/tool_usage.txt
cat /tmp/tool_usage.txt
```

### 1.2 Analyze Skill Loading
```bash
# Which skills are loaded and how often (portable grep)
while IFS= read -r audit_file; do
  [ -z "$audit_file" ] && continue
  [ -f "$audit_file" ] || continue
  grep "final_name='skill'" "$audit_file" 2>/dev/null
done < /tmp/skill_audit_files.txt | \
  grep -oE "skill_name[^,]*" | sort | uniq -c | sort -rn

# Count skill calls per log (last 20 sessions)
head -20 /tmp/skill_audit_files.txt | while IFS= read -r audit_file; do
  [ -z "$audit_file" ] && continue
  [ -f "$audit_file" ] || continue
  count=$(grep -c "final_name='skill'" "$audit_file" 2>/dev/null || echo 0)
  if [ "$count" -gt 0 ]; then
    echo "$(basename $audit_file): $count skill calls"
  fi
done
```

### 1.3 Identify Repeated Patterns
```bash
# Look at tool call sequences — what tools are used together?
# Sample from recent logs (portable grep)
head -20 /tmp/skill_audit_files.txt | while IFS= read -r audit_file; do
  [ -z "$audit_file" ] && continue
  [ -f "$audit_file" ] || continue
  grep -oE "final_name='[^']*" "$audit_file" 2>/dev/null | sed "s/final_name='"// | uniq -c | sort -rn
done
```

### 1.4 Extract USER Prompts
```bash
# What tasks are being done?
head -20 /tmp/skill_audit_files.txt | while IFS= read -r audit_file; do
  [ -z "$audit_file" ] && continue
  [ -f "$audit_file" ] || continue
  grep -A1 "^\[.*\] USER" "$audit_file" 2>/dev/null | grep "|" | \
    grep -v "Think hard" | grep -v "EVERY TIME" | head -3
done | sort -u
```

---

## Phase 2: Skill Audit

### 2.1 List All Skills
```bash
# List all skill directories and their SKILL.md files
ls -d skills/*/SKILL.md 2>/dev/null || ls skills/*/SKILL.md
```

### 2.2 Check Skill Quality
For EACH skill file, verify:
- [ ] Has YAML frontmatter with `name`, `description`, `category`
- [ ] Description includes "(also load: related_skills)" for cross-references
- [ ] Concise — no obvious content, no tutorials
- [ ] Self-audience — assumes reader knows basics
- [ ] Has "Related Skills" section with cross-references
- [ ] Actionable — clear when to use, what to do

### 2.3 Rewrite Skills (if needed)
Use `caveman` skill for style. Apply:
- Drop articles (a, an, the)
- Remove fillers (just, really, basically)
- No pleasantries
- Fragments OK
- Code unchanged

For EACH skill:
1. Read current content
2. Remove obvious/redundant content
3. Keep only project-specific knowledge
4. Add cross-references to related skills
5. Verify frontmatter is correct

### 2.4 Skill helper (.py) files
For each skill, think if there should be helper files (in parallel with SKILL.md).
Feel free to be creative, maybe some .py code directly belonging to the skill, or .sh code?
If yes, create, update, improve.

---

## Phase 3: Skill Findability

### 3.1 Verify Descriptions, examples:
Each skill's `description` field must contain keywords that would trigger it:
- `code-review-workflow`: "review code", "check quality", "audit codebase"
- `test-suite-monitor`: "run tests", "monitor tests", "background tests"
- `git`: "git operations", "worktree", "branch management"


### 3.2 Cross-Reference Check, examples:
Verify each skill links to related skills:
- `background` ↔ `tmux_monitoring` ↔ `test-suite-monitor`
- `review` ↔ `code-review-workflow` ↔ `python_best_practices`
- `tau_testsuite` ↔ `test-suite-monitor` ↔ `background`
- `ast-grep` ↔ `code-review-workflow`

### 3.3 Description
Ensure skill description is clear and suitable for finding.

---

## Phase 4: Identify Missing Skills

### 4.1 Analyze Tool Call Gaps
Look for high-frequency tool sequences that lack a corresponding skill:
```bash
# Find tools used frequently without skill coverage
# Compare tool_usage.txt against existing skills
```

### 4.2 Pattern Detection
For each repeated pattern:
1. Does a skill exist for it?
2. If not, create one
3. If yes, is it being loaded?
4. If not, why? (poor description? missing keywords?)

### 4.3 New Skill Creation
For each identified gap:
1. Create skill file with proper frontmatter
2. Write concise content (caveman style)
3. Add cross-references
4. Verify description contains search keywords

### 4.4 Skill Maintenance
Make sure to review and update also this _tauskillmaintenance.md skill, try to improve it, how can we do more? better?

---

## Phase 5: Verification

### 5.1 Test Skill Discovery
```bash
# Verify all skills are discoverable
skill  # List all skills
skill "review"  # Search by keyword
skill "test"     # Search by keyword
skill "background"  # Search by keyword
```

### 5.2 Verify Cross-References
For EACH skill, verify "Related Skills" section exists and links are valid:
```bash
for f in skills/*/SKILL.md; do
  if ! grep -q "## Related Skills" "$f"; then
    echo "MISSING Related Skills: $(basename $(dirname $f))"
  fi
done
```

### 5.3 Final Checklist
- [ ] All skills have proper frontmatter
- [ ] All skills have "Related Skills" section
- [ ] All descriptions contain search keywords
- [ ] Cross-references are bidirectional
- [ ] No obvious/redundant content remains
- [ ] New skills created for identified gaps
- [ ] Skills are discoverable via keyword search

---

## Output Format

After completing all phases, produce:
```
=== SKILL MAINTENANCE REPORT ===
## Audit Log Analysis
- Total tool calls: [count]
- Skill calls: [count]
- Skills loaded: [list]
- Repeated patterns: [list]

## Skill Audit
- Skills reviewed: [count]
- Skills rewritten: [count]
- Issues found: [list]

## Findability
- Descriptions updated: [count]
- Cross-references added: [count]
- Keywords missing: [list]

## New Skills
- Created: [list with purposes]
- Patterns addressed: [list]

## Recommendations
- [actionable items]
```
