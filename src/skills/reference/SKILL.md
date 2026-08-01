---
name: reference
description: Tau quick reference — commands, configs, patterns, audit log patterns (also load: command_template, shell_scripting, skill_template)
category: reference
keywords: reference, cheat sheet, quick lookup, commands, config, patterns, audit
---

# Reference

## When
"quick reference", "cheat sheet", "tau commands", "tau config", "tau patterns"

## Tau Commands (user-facing, not agent tools)
```
/fork <task>                          # Spawn fork (full memory) — agent uses `fork` tool
/subagent <task>                      # Spawn subagent (blank slate) — agent uses `subagent` tool
/background <cmd>                     # Run background task
/status                               # Agent status
/plan <action>                        # Plan tool
```

## Tau Config
| Key | Value |
|-----|-------|
| Log dir | `~/.local/tau/log/` |
| Skills dir | `skills/` |
| Tools dir | `tools/` |
| Commands dir | `commands/` |
| Test dir | `$HOME/tau/test/` |
| Src dir | `$HOME/tau/src/` |

## Audit Log Patterns
```bash
grep -oP "final_name='[^']*" ~/.local/tau/log/*.audit | sed "s/final_name='"// | sort | uniq -c | sort -rn
grep -rh '"skill_name":\s*"[^"]*"' ~/.local/tau/log/*.audit | grep -oP '"skill_name":\s*"\K[^"]+' | sort | uniq -c | sort -rn
```

## Helper
```bash
python3 skills/reference/ref_helper.py  # Quick reference lookup
```

## Related Skills
- `command_template` — command creation format
- `shell_scripting` — shell patterns
- `skill_template` — skill creation format
