---
name: file-ops
description: "File operations — read, edit, write, glob, ls, head, wc. Read file, write file, edit file, find files (also load: code-review-workflow, search-replace, git, grep_tool, shell_scripting)"
category: development
keywords: file, read, write, edit, glob, list, directory, batch, find, operations
---

# File Operations

## When
"read file", "edit file", "write file", "find files", "list directory", "file workflow", "batch edit", "wc", "word count", "count lines", "head file", "file_append", "file operations"

## Patterns

### Read → Edit → Verify
```bash
file_read(path="file.py")
file_edit(path="file.py", old="x", new="y")
grep -n "y" file.py
```

### Batch
```bash
glob(pattern="*.py")
for f in *.py; do grep "TODO" "$f"; done
ls -la *.py
```

### Safe Write
```bash
file_write(path="new.py", content="...")
file_read(path="new.py")  # Verify
```

## Rules
- Read before edit — full context
- Verify after edit — grep changes
- Glob for batch — find all matches
- ls for exploration

## Helper
```bash
python3 skills/file-ops/file_ops.py  # file ops helper
```

## Related Skills
- `code-review-workflow` — verify changes
- `search-replace` — find and replace patterns
- `git` — commit file changes
- `grep_tool` — search file contents
- `shell_scripting` — batch file operations
