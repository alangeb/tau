---
category: communication
description: "Caveman writing style — drop articles, use fragments, compress text, maximize info density per token, concise (also load: _taudoc, code-simplifier, documentation, readme_template, skill_template, prompt-crafting, skill_tool, tauskillmaintenance, tool_template)"
keywords: terse writing, text compression, drop articles, info density, compressed text, writing style, fragment writing, concise communication, token efficiency
name: caveman
---

# caveman

## When
"write concisely" | "shorter output" | "be brief" | "caveman style" | "drop articles" | "write a script" | "write file"

## Rules
- Drop articles, pronouns, filler
- Fragments, imperatives OK
- No "I think", "It seems", "Note that"
- Preserve technical accuracy, code, numbers
- Maximize info density per token

## Examples
- Bad: "I think the issue is that the function is not returning the correct value."
- Good: "Function returns wrong value."
- Bad: "Let me check the file to see what's going on."
- Good: "Checking file."

## Helpers
```bash
python3 skills/caveman/compress.py <input> [output]        # Compress single file
python3 skills/caveman/style_check.py <file.txt>           # Check violations
python3 skills/caveman/batch_compress.py <f1> [f2 ...]     # Batch compress multiple
python3 skills/caveman/batch_compress.py *.md --dry-run    # Preview changes
```

## Related Skills
- `skill_tool` — list and load skills
- `command_template` — writing concise commands
- `skill_template` — writing concise skills
- `documentation` — write concise docs
- `code-simplifier` — simplifying code style
- `prompt-crafting` — concise writing style for prompts
- `tauskillmaintenance` — skill quality audit
- `tool_template` — concise writing for tools
