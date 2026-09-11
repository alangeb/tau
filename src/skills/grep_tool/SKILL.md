---
category: search
description: "Search files for patterns — regex grep, recursive search, find function callers, locate callbacks, find text across codebase (also load: ast-grep, file-ops, search-replace, tau_audit, data_processing, security-audit, shell_scripting, web-research, wiki)"
keywords: grep, text search, regex search, recursive search, pattern search, count matches, context lines, file search, text pattern
name: grep_tool
---

# grep Tool

## When
"search files" "find text" "grep pattern" "regex search" "recursive grep" "search code" "grep" "find pattern" "search for text" "search the web"

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
- Agent's `grep` tool ≠ bash `grep` — use tool for structured search
- Large repos: ALWAYS `--exclude-dir={venv,__pycache__,.git,node_modules}`
- Audit logs: `grep -rn "TOOL_ERROR" ~/.local/tau/log/*.audit`
- Skill cross-refs: `grep -rn "also load" skills/*/SKILL.md`

## Helper
```bash
source skills/grep_tool/grep_patterns.sh
python3 skills/grep_tool/grep_structured.py <pattern> [dir] [--json] [--count] [--context N]  # structured grep
```
Agent's `grep` tool — structured search (recursive, regex, context).

## Related Skills
- `ast-grep` — AST-based search (structural)
- `search-replace` — search and replace patterns, bulk edit files
- `bug_investigation` — trace call sites, execution paths, traceback pattern search
- `data_processing` — Structured data processing
- `file-ops` — file operations
- `refactor` — search/replace during refactoring
- `search-replace` — find and replace patterns
- `security-audit` — credential scanning
- `shell_scripting` — shell patterns
- `tau_audit` — audit log grep patterns
- `web-research` — web content extraction
- `wiki` — knowledge storage
