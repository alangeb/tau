---
category: development
description: "Search and replace patterns — regex substitution, multi-file find/replace, glob matching, bulk batch (also load: grep_tool, file-ops, refactor, edit-and-run)"
keywords: regex pattern substitution, bulk text replacement, file_edit tool usage, grep verification, multi-file find replace, batch operations, bulk file editing, glob pattern matching, multi-file editing, file batch processing
name: search-replace
---

# Search Replace

## When
"find and replace" "update pattern" "search and modify" "bulk edit" "rename variable" "change all occurrences" "find pattern" "search files" "edit file" "batch edit" "bulk modify" "edit multiple files" "glob and edit" "multi-file changes" "bulk search replace"

## Sequence
1. **Find** — `glob(pattern="**/*.py")` or `grep -rn "pattern" . --include="*.py" -l`
2. **Review** — `file_read` sample files, verify pattern matches
3. **Edit** — `file_edit` each file with old_string/new_string
4. **Verify** — `grep -rn "pattern" .` confirms changes, count matches

```bash
python3 skills/search-replace/find_replace.py "old" "new" <path>  # Find + replace + verify
# Or manual:
grep -rn "pattern" .        # Find
file_edit(path="<file>", old="old", new="new")  # Edit
grep -rn "pattern" .        # Verify
```

## Quick Patterns
```bash
# Find all files matching glob
glob(pattern="**/*.py")

# Find files containing text
grep(pattern="pattern", path=".", recursive=True)

# Bulk edit loop
for file in $(grep -rl "pattern" . --include="*.py"); do
  file_edit(file_path="$file", old="old", new="new")
done

# Verify changes
grep -c "new_pattern" . --include="*.py" -r
```

## Complex Patterns
AST-level: use `ast-grep`:
```bash
ast-grep -p '$A && $A()' --rewrite '$A?.()' -U src/
```

## Checklist
- [ ] All target files identified
- [ ] All occurrences found
- [ ] Sample files reviewed
- [ ] Context reviewed
- [ ] Changes applied
- [ ] Verified with grep
- [ ] No unintended changes

## Helper
```bash
python3 skills/search-replace/find_replace.py "pattern" [path] [file_pattern]  # Find + count
python3 skills/search-replace/bulk_edit.py "pattern" "old" "new" <path>  # Find + replace + verify
```

## Related Skills
- `edit-and-run` — edit, test, iterate loop
- `ast-grep` — complex AST search/rewrite
- `code-review-workflow` — verify changes
- `file-ops` — file read/edit patterns
- `git-verify` — confirm modifications
- `shell_scripting` — automate search/replace workflows
- `refactor` — larger-scale restructuring
- `grep_tool` — search patterns before replacing
- `tauskillmaintenance` — skill quality maintenance
