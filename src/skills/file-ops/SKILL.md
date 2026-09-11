---
category: development
description: "File operations — file_read, file_write, file_edit, glob, ls, head, wc for reading, writing, editing, finding files (also load: grep_tool, search-replace, bug_investigation, shell_scripting)"
keywords: file_read tool, file_write tool, file_edit tool, glob pattern matching, ls directory listing, wc line counting
name: file-ops
---

# File Operations

## When
"read file" | "edit file" | "write file" | "find files" | "list directory" | "file workflow" | "batch edit" | "wc" | "word count" | "count lines" | "head file" | "file_append" | "file operations" | "list files" | "search files" | "find pattern"

## Rules
- `file_read` with limit=100 default; use offset for large files
- `file_edit` requires exact old_string match — verify with grep first
- `file_write` auto-creates parent dirs
- `glob(pattern="**/*.py", recursive=True)` for batch

## Helpers
```bash
python3 skills/file-ops/file_ops.py  # file ops helper
source skills/file-ops/file_ops_helpers.sh  # fo_find, fo_wcl, fo_largest, fo_recent, fo_diff, fo_duplicates, fo_rename
```

## Related Skills
- `data_processing` — Structured data processing
- `code-review-workflow` — verify changes
- `search-replace` — find and replace patterns
- `git` — commit file changes
- `grep_tool` — search file contents
- `shell_scripting` — batch file operations
- `python_best_practices` — linting/formatting installed tools
- `project-onboard` — discover project dependencies
- `search-replace` — search and replace patterns, bulk edit files
- `bug_investigation` — traceback parsing and file inspection
- `edit-and-run` — edit code, test, iterate
