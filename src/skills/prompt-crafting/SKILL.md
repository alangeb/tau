---
name: prompt-crafting
description: "Write effective prompts for subagent, fork, background delegation. Prompt engineering, task instructions, clear scope, context passing, delegation quality (also load: delegation, context_management, task_creation, caveman)"
category: workflow
keywords: prompt, prompt engineering, subagent prompt, fork prompt, delegation, task instructions, context passing
---

# Prompt Crafting

## When
"write prompt", "subagent prompt", "fork prompt", "delegation prompt", "task instructions", "prompt template"

## Rules
- **Specific**: say exactly what to do, where, how
- **Context**: include file paths, relevant code, current state
- **Success criteria**: define what "done" looks like
- **Constraints**: say what NOT to do
- **One task per prompt**: don't mix unrelated work

## Subagent Template (Blank Slate — Knows NOTHING)
```
TASK: [what to do] | CONTEXT: [file paths, code, state] | CONSTRAINTS: [limits] | OUTPUT: [format] | VERIFY: [how to confirm]
```

## Fork Template (Has Memory — Focus, Don't Repeat)
```
FOCUS ON: [what to do] | SKIP: [don't re-explain] | DELIVER: [output expected]
```

## Background — Self-Contained Command
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
- `delegation`, `context_management`, `task_creation`, `caveman`
