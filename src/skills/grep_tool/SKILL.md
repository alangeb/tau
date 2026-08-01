---
name: grep_tool
description: "grep search patterns — recursive search, regex, context, count, invert. Find text in files, pattern matching, grep flags (also load: ast-grep, file-ops, search-replace, shell_scripting, bug_investigation)"
category: search
keywords: grep, search, pattern, regex, recursive, find text, file search, context, count, invert, -r, -n, -i, -E, -v, -c, --include, --exclude
---

# grep Tool

## When
"search files", "find text", "grep pattern", "regex search", "recursive grep", "search code"

## Agent Patterns
```bash
grep -rn --include="*.py" "pattern" .                    # Python only
grep -rn --exclude-dir={venv,__pycache__,.git,node_modules} "pattern" .  # Exclude noise
grep -rn -E "pat1|pat2|pat3" .                           # Multi-pattern OR
grep -rn -c "pattern" .                                  # Count per file
grep -rn -w "exact_word" .                               # Whole word
grep -rn -I --binary-files=without-match "pattern" .     # Skip binary
grep -rn -l "pattern" .                                  # File list only (pipe to xargs)
grep -rn -L "pattern" .                                  # Files without match
```

## Cross-File Search
```bash
# Find callers of a function
grep -rn "function_name(" . --include="*.py" | grep -v "def function_name"

# Find callback assignments
grep -rn "= function_name" . --include="*.py" | grep -v "def"

# Find threading targets
grep -rn "target=function_name" . --include="*.py"

# Search git diff for patterns
git diff HEAD | grep -E "print\(|breakpoint\(|import pdb"
```

## Gotchas
- `-P` (Perl regex) not portable — use `-E` (extended)
- Large repos: ALWAYS `--exclude-dir` for venv, __pycache__, .git, node_modules
- Binary files: add `-I` or `--binary-files=without-match`
- Special chars in pattern: quote or escape
- `grep -rn` vs `rg` (ripgrep): rg faster, not always installed
- Empty results: verify with `--include` glob matches files

## Helper
No helper needed — grep is shell-native. Use agent's `grep` tool for structured search.

## Related Skills
- `ast-grep` — AST-based search (structural)
- `file-ops` — file operations
- `search-replace` — find and replace patterns
- `shell_scripting` — shell patterns
- `bug_investigation` — trace call sites and execution paths
