---
name: edit-and-run
description: "Edit code, test, iterate loop — read, change, verify cycle (also load: shell_scripting, search-replace, debug, error-recovery)"
category: workflow
keywords: edit code, fix and test, iterate on changes, debug loop, make changes and verify, read edit run, trial and error, fix lint, debug test
---

# Edit and Run

## When
"edit code", "fix and test", "iterate on changes", "debug loop", "make changes and verify", "fix lint errors", "debug test failures"

## Pattern
Core loop: read → edit → run → assess → repeat
```
1. file_read(path="...")                    # Understand current state
2. file_edit(path="...", old="...", new="") # Targeted change
3. bash(cmd="pytest ...")                   # Test / verify
4. Assess output — pass? done. Fail? goto 1
```

## Rules
- Read BEFORE edit — never guess file content
- Small edits — one change per cycle
- Run immediately after edit — no batching
- Read error output — locate exact line
- Fix root cause — not symptom
- Stop when clean — no over-engineering

## Common Scenarios

### Fix Lint Errors
```
bash(cmd="ruff check file.py")              # Find issues
file_read(path="file.py", limit=20, offset=N)  # Read problem area
file_edit(path="file.py", old="...", new="")   # Fix
bash(cmd="ruff check file.py")              # Verify clean
```

### Debug Test Failures
```
bash(cmd="pytest test_file.py::test_name -v")   # Run failing test
file_read(path="test_file.py", limit=40)         # Read test
file_read(path="src_file.py", limit=40)          # Read source
file_edit(path="src_file.py", old="...", new="") # Fix
bash(cmd="pytest test_file.py::test_name -v")    # Verify pass
```

### Fix Import Errors
```
bash(cmd="python3 file.py")                       # Get traceback
file_read(path="file.py", limit=15)               # Read imports
file_edit(path="file.py", old="...", new="")      # Fix import
bash(cmd="python3 file.py")                       # Verify
```

## Helper
```bash
python3 skills/edit-and-run/edit_run.py <file> <old> <new>  # Edit and verify
```

## Tips
- Use `offset` + `limit` in file_read — target problem area
- Use `old_string` exactly — match whitespace, quotes
- Keep bash commands small — single test, single file
- If edit fails (old_string mismatch), re-read file first
- Use `grep` to find exact text before editing

## Anti-Patterns
- Editing without reading first | Multiple edits without testing | Ignoring error output | Guessing at old_string | Running full test suite for single change

## Related Skills
- `debug` — systematic debug
- `error-recovery` — handle failures
- `file-ops` — file manipulation
- `git` — commit after fix
- `search-replace` — text transformations
- `shell_scripting` — bash commands
