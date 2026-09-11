---
category: workflow
description: "Write effective delegation prompts and instruction templates for subagent, fork, background tasks (also load: delegation, caveman, skill_template, task)"
keywords: prompt crafting, delegation prompts, subagent prompts, fork prompts, task prompts, prompt engineering, context constraints, success criteria
name: prompt-crafting
---

# Prompt Crafting

## When
"write prompt" | "subagent prompt" | "fork prompt" | "delegation prompt" | "task instructions" | "prompt template" | "prompt" | "prompt engineering" | "craft prompt"

## Rules
- **Specific**: say exactly what to do, where, how
- **Context**: include file paths, relevant code, current state
- **Success criteria**: define what "done" looks like
- **Constraints**: say what NOT to do
- **One task per prompt**: don't mix unrelated work

## Templates
### Subagent (Blank Slate — Knows NOTHING)
```
TASK: [what to do] | CONTEXT: [file paths, code, state] | CONSTRAINTS: [limits] | OUTPUT: [format] | VERIFY: [how to confirm]
```

### Fork (Has Memory — Focus, Don't Repeat)
```
FOCUS ON: [what to do] | SKIP: [don't re-explain] | DELIVER: [output expected]
```

### Background — Self-Contained Command
```
Command: self-contained, idempotent, output status clearly
Keywords for wait: "success|error|done|FAILED|Traceback"
```

## Anti-Patterns
- Vague: "fix the code" → "fix TypeError in file.py line 42"
- Missing context: "run tests" → "cd tests/ && pytest test_xxx.py -v"
- No success criteria: "refactor this" → "refactor X, keep tests green"
- Too broad: "review the project" → "review auth.py for unused imports"
- Assuming knowledge: subagent knows NOTHING — include everything

## Choose Right Tool
| Situation | Use | Prompt Style |
|-----------|-----|-------------|
| Isolated, well-defined | `subagent` | Full template: task+context+constraints |
| Needs conversation history | `fork` | Focus+skip+deliver (short) |
| Long-running shell work | `background` | Self-contained command + keywords |

## Helpers
```bash
python3 skills/prompt-crafting/prompt_template.py {subagent|fork} "task description"
python3 skills/prompt-crafting/prompt_template.py --check "fix the code"
```

## Related Skills
- `background` — Run commands in background
- `caveman` — Concise writing style for prompts
- `context_management` — Context capacity optimization
- `delegation` — Delegation patterns and tool selection
- `skill_template` — Skill creation format
- `task` — Creating tasks for dream execution (redirect: see task)
- `task` — Task framework, lifecycle, verification
