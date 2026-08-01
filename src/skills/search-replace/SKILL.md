---
name: search-replace
description: "Find and replace patterns across files — grep, file_read, file_edit, verify. Text substitution, bulk edit, refactoring (also load: ast-grep, code-review-workflow, file-ops, git-verify, grep_tool, shell_scripting)"
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
grep -rn "pattern" .        # Find
file_edit(path="<file>", old="old", new="new")  # Edit
grep -rn "pattern" .        # Verify
```

## Complex Patterns
For AST-level search/replace, use `ast-grep`:
```bash
ast-grep -p '$A && $A()' --rewrite '$A?.()' -U src/
```

## Checklist
- [ ] All occurrences found
- [ ] Context reviewed
- [ ] Verified with grep
- [ ] No unintended changes

## Related Skills
- `ast-grep` — complex AST search/rewrite
- `code-review-workflow` — verify changes
- `file-ops` — file read/edit patterns
- `git-verify` — confirm modifications
- `shell_scripting` — automate search/replace workflows
