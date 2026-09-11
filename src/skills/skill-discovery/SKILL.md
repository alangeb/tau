---
name: skill-discovery
description: "Auto-discover and find relevant skills — keyword matching, prompt analysis, skill suggestion (also load: skill_tool, skill_template, tauskillmaintenance, reference, dream)"
category: discovery
keywords: skill discovery, find skill, task to skill, keyword match, prompt analysis, skill suggestion, relevant skill, skill search, skill recommendation
---

# skill-discovery

## When
User asks anything and you're not sure which skill to load. ALWAYS run discovery before starting work.

## Skill Discovery Algorithm
1. **Extract keywords** from user prompt (nouns, verbs, domain terms)
2. **Match** against skill names, descriptions, keywords in all 64+ skills
3. **Load top 3** matching skills via `skill("skill-name")`
4. **Cross-reference** — check `(also load: ...)` in matched skills for related ones
5. **Verify** — after loading, confirm skill covers the task; if not, search again

## Common Task → Skill Mapping
| Task Type | Load These Skills |
|-----------|-------------------|
| Code review | `code-review-workflow`, `python_best_practices` |
| Python analysis | `pyprep`, `python_best_practices` |
| Git operations | `git`, `git-advanced`, `git-verify` |
| Background tasks | `background`, `tmux_monitoring` |
| Debugging | `bug_investigation`, `debug` |
| Planning | `manifest`, `plan_template` |
| Delegation | `delegation`, `prompt-crafting` |
| Documentation | `documentation`, `readme_template` |
| Docker | `docker` |
| Testing | `tau_testsuite`, `test-suite-monitor` |
| Web research | `web-research` |
| Security | `security-audit` |
| Shell scripting | `shell_scripting` |
| Image tasks | `image` |

## Auto-Load Pattern
```
ON any task:
  1. skill("")  # list all skills
  2. Match prompt keywords to skill names/descriptions
  3. skill("best-match")  # load top match
  4. Check (also load: ...) for related skills
  5. Load those too
```

## Helper — skill_finder.py
```bash
python3 ~/.local/tau/skills/skill_tool/skill_finder.py search "keyword"
python3 ~/.local/tau/skills/skill_tool/skill_finder.py list
```

## Helper
```bash
python3 skills/skill-discovery/discover.py              # List all skills
python3 skills/skill-discovery/discover.py "code review" # Search by keywords
python3 skills/skill-discovery/discover.py "debug python" # Multi-keyword search
```

## Related Skills
- `background` — background tmux sessions
- `bug_investigation` — error tracing
- `code-review-workflow` — code analysis
- `debug` — debug Python issues
- `delegation` — delegate work
- `documentation` — write docs
- `docker` — containers
- `git` — git operations
- `git-advanced` — git bisect, cherry-pick
- `git-verify` — verify changes
- `image` — image analysis
- `plan_template` — task plans
- `manifest` — task tracking, goal management
- `prompt-crafting` — delegation prompts
- `pyprep` — Python analysis
- `python_best_practices` — ruff, black, mypy
- `readme_template` — README files
- `security-audit` — security scan
- `shell_scripting` — bash scripts
- `skill_template` — skill format
- `skill_tool` — list and load skills
- `tauskillmaintenance` — skill maintenance
- `test-suite-monitor` — monitor tests
- `testing` — pytest tests
- `tmux_monitoring` — tmux sessions
- `web-research` — web search
