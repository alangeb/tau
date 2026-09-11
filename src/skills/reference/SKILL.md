---
category: reference
description: "Quick reference for tau commands, config paths, directory layout, and audit log grep patterns (also load: command_template, security-audit, shell_scripting, tau_audit, skill-discovery)"
keywords: tau CLI invocation, tau.json configuration, directory structure layout, audit log grep patterns, skill tool reference
name: reference
---



# Reference

## When
"quick reference"
"cheat sheet"
"tau commands"
"tau config"
"tau patterns"
"code review"
"write a script"
"shell script"
"bash command"
## Commands
```
/fork <task>                          # Spawn fork (full memory)
/subagent <task>                      # Spawn subagent (blank slate)
/background <cmd>                     # Run background task
/status                               # Agent status
/manifests                            # List manifests, show hierarchy
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
python3 skills/reference/ref_helper.py
```

## Related Skills
- `skill-discovery` — auto-discover relevant skills
- `command_template` — Command creation format
- `shell_scripting` — Shell patterns
- `skill_template` — Skill creation format
- `tau_audit` — audit log analysis patterns
- `security-audit` — security scanning reference
