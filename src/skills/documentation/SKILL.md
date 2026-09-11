---
category: documentation
description: "Write docs, create documentation, docstrings, changelog, release notes, readme files (also load: _taudoc, caveman, readme_template, spec, tool_template, release_management, skill_template, wiki)"
keywords: documentation, docstrings, changelog, release notes, readme, write docs, technical writing, project documentation
name: documentation
---

# Documentation

## When
"write docstring" | "document code" | "changelog" | "release notes" | "write docs" | "docstrings" | "documentation" | "doc" | "readme" | "write file" | "write a script"

## Tau Doc Standards
- Tool descriptions: one line, markdown, no code blocks
- Skill descriptions: include "(also load: _taudoc, caveman, readme_template, spec, tool_template, release_management, skill_template, wiki)" refs
- AGENT.md: NEVER modify except TAU.md reference
- designs/: ALL design docs live here
- Use `caveman` skill for concise prose

## Helper
```bash
python3 skills/documentation/doc_helper.py  # documentation helper
```

## Related Skills
- `_taudoc` — project documentation structure
- `readme_template` — README documentation
- `caveman` — write concise docs
- `code-review-workflow` — review documentation quality
- `skill_template` — skill creation format
- `wiki` — knowledge storage and retrieval
- `sum` — State summarization
- `image` — image handling in docs
- `spec` — spec-driven documentation, ADR, system design
- `release_management` — Version bumping, changelog, release notes
