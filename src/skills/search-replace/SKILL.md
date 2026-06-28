---
name: search-replace
description: Find and replace patterns across files — grep, file_read, file_edit, verify. Find replace, text substitution, bulk edit, refactoring, rename variable (also load: ast-grep, file-ops, code-review-workflow, git-verify)
category: development
keywords: search, replace, find, substitute, bulk edit, refactoring, rename, occurrences
---

# Search Replace

## When
"find and replace", "update pattern", "search and modify", "bulk edit", "rename variable", "change all occurrences"

## Sequence
```bash
python3 skills/search-replace/find_replace.py "old" "new" <path>  # Find + replace + verify
# Or manual:
grep -rn "pattern" .                        # Find occurrences
file_read(path="<file>")                   # Read context
file_edit(path="<file>", old="old", new="new")  # Edit
grep -rn "pattern" .                       # Verify
```

## Complex Patterns
For AST-level search/replace, use `ast-grep` instead:
```bash
ast-grep -p '$A && $A()' --rewrite '$A?.()' -U src/
```

## Checklist
- [ ] All occurrences found
- [ ] Context reviewed before editing
- [ ] Edits verified with grep
- [ ] No unintended changes

## Related Skills
- `ast-grep` — complex AST search/rewrite
- `code-review-workflow` — verify changes
- `git-verify` — confirm modifications
- `file-ops` — file read/edit patterns
- `shell_scripting` — automate search/replace workflows

- `agent-browser` — Browser automation CLI for AI agents