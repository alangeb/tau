# Periodic Skill Maintenance — Audit Report

**Date:** 2026-08-07
**Scope:** Last 50 audit sessions, 58 skills in ~/.local/tau/skills/, 62 skills in src/skills/

---

## 1. Tool Usage Distribution (50 recent sessions, ~8,500 total calls)

| Tool | Count | % | Notes |
|------|-------|---|-------|
| bash | 4,944 | 58% | Dominant — most work done via shell |
| file_read | 753 | 9% | File inspection |
| plan | 626 | 7% | Task planning |
| file_edit | 179 | 2% | Targeted edits |
| subagent | 139 | 1.6% | Delegation |
| grep | 139 | 1.6% | Search |
| ls | 127 | 1.5% | Directory listing |
| file_write | 105 | 1.2% | File creation |
| background_exec | 88 | 1% | Tmux execution |
| glob | 85 | 1% | File finding |
| info | 47 | 0.6% | Agent info |
| fork | 47 | 0.6% | Fork delegation |
| background_wait | 44 | 0.5% | Tmux waiting |
| background_run | 19 | 0.2% | Background tasks |
| **skill** | **12** | **0.14%** | **VERY LOW USAGE** |
| think | 10 | 0.1% | Reasoning |
| wiki | 2 | 0.02% | Wiki management |
| pyscan | 1 | 0.01% | Python analysis |

### Key Finding: Skills are loaded in only ~4% of sessions (2 out of 50). The skill tool accounts for 0.14% of all tool calls.

---

## 2. Skill Loading Details

| Skill Name | Loads | Context |
|------------|-------|---------|
| (empty — list all) | 1 | Skill listing |
| wiki | 1 | Wiki lookup |
| — | 10 | False positives (bash commands containing "skill" string) |

**Total genuine skill loads: 2 across 50 sessions.**

### Skills with Highest Potential Usage (based on tool patterns)
- **background** — 151 background_* tool calls but skill rarely loaded
- **python_analysis** — 1 pyscan call, many Python projects worked on
- **git** — git operations via bash, not skill
- **code-review-workflow** — review work done ad-hoc
- **delegation** — 186 subagent/fork calls without skill guidance

---

## 3. Skill Inventory Comparison

### Skills only in `src/skills/` (NOT in ~/.local/tau/skills/):
- debug, gitcrit, health, manifest, orchestrate, pyprep, python_workflow, refactor, sum

### Skills only in `~/.local/tau/skills/` (NOT in src/skills/):
- edit-and-run, grep_tool, info, native_tools, plan_tool, readme_template, search-replace, shell_scripting, signal-cli, skill_tool, _spec, spec, task_creation, tau_testsuite, test-suite-monitor, tmux_monitoring, tool_template, web-research

### Skills in both (58 total):
Most skills are synced. Divergence suggests some skills are being developed in one location but not synced.

---

## 4. Previous Audit Findings (Jul 27) — Status

| Finding | Status | Action Needed |
|---------|--------|---------------|
| wiki-maintenance/ = REDUNDANT wrappers | Still present | DELETE or merge |
| tau_audit/ = BLOATED (3 overlapping scripts) | Still present | Merge into analyze_audit.py |
| code-simplifier/simplify.py = STUB | Still present | Complete or remove |
| background/session_helpers.sh = STUB | Still present | Complete or remove |

---

## 5. Tool Call Quality

- **Tool fixes applied:** Only `file_read(path)` → `file_path` alias resolution (5 instances)
- **No skill-related errors** in recent logs
- **No tool call failures** detected in recent sessions

---

## 6. Recommendations

### High Priority
1. **Increase skill usage** — Skills are loaded in 2% of sessions. The AGENT.md says "Use `skill` tools" and "MUST: Use `skill` tools", but compliance is near zero. Consider:
   - Adding skill loading prompts to AGENT.md for common workflows
   - Pre-loading skills for known task types
   
2. **Clean up redundant skills** — Delete `wiki-maintenance/` (7 wrapper files, ~526 lines of dead code)

3. **Sync skill directories** — `src/skills/` and `~/.local/tau/skills/` have diverged (10 vs 18 unique skills)

### Medium Priority
4. **Merge tau_audit/ bloat** — 3 overlapping analysis scripts (~1,700 lines) could be merged
5. **Complete or remove stubs** — code-simplifier/simplify.py and background/session_helpers.sh
6. **Audit never-used skills** — Many of 58 skills have zero loads; consider archiving

### Low Priority
7. **Skill findability** — Empty skill_name loads are rare; agents don't explore available skills
8. **Add usage metrics** to each skill's SKILL.md

---

## 7. User Prompt Patterns (sampled)

Recent user tasks:
- Periodic Skill Maintenance (this task)
- Code reading and summarization (PACKING.md)
- Build system investigation
- Math (1+1)
- Plan review and deep thinking
- Project understanding

**Observation:** Most tasks are handled via bash + file_read + plan without skill assistance.
