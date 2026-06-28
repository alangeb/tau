---
name: caveman
description: Make output concise — drop articles, remove filler, speak caveman style. Concise, brief, short, compress, terse (also load: command_template, skill_template, tauskillmaintenance)
category: communication
keywords: concise, brief, short, compress, terse, drop articles, remove filler
---

# Concise Communication

## When
"write concisely", "shorter output", "be brief", "caveman style", "drop articles"

## Rules
- Omit articles, pronouns, filler words
- Use fragments, imperatives
- No "I think", "It seems", "Note that"
- Preserve technical accuracy, code, numbers
- Maximize information density per token

## Examples
- Bad: "I think the issue is that the function is not returning the correct value."
- Good: "Function returns wrong value."
- Bad: "Let me check the file to see what's going on."
- Good: "Checking file."

## Helpers
```bash
python3 skills/caveman/style_check.py <file.txt>  # Check caveman style violations
python3 skills/caveman/compress.py <input> [output]  # Compress text
```

## Related Skills
- `command_template` — writing concise commands
- `skill_template` — writing concise skills
- `code-simplifier` — simplifying code style
- `tauskillmaintenance` — audit skill content for conciseness
