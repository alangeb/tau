---
description: "search code patterns, structural search, pattern match and replace with ast-grep (also load: grep_tool, refactor, code-review-workflow, debug)"
keywords: AST pattern matching, structural AST search, pattern rewrite, abstract syntax tree queries, AST transformation
name: ast-grep
category: development
---

# ast-grep

## When
"AST search" "structural search" "code pattern search" "rewrite code pattern" "code review" "python analysis" "search files" "find pattern" "review code"

## Search
```bash
ast-grep -p '$A.context' agent_core.py    # field access
ast-grep -p '$FUNC(' tools/               # function calls
ast-grep -p 'class TauErgon' .            # class definition
```

## Replace
```bash
ast-grep -p '$A && $A()' --rewrite '$A?.()' -U src/
ast-grep -p '$A || $A()' --rewrite '$A ?? $A' -U src/
```

## Blind Spots — VERIFY with grep
- Thread targets: `grep -rn "target="`
- Callbacks: `grep -rn "= fn" | grep -v def`
- Higher-order: `grep -rn "map(\|filter(\|reduce("`
- String refs / eval: `grep -rn '"fn_name"'`

Triple-check: AST flags → grep confirms → manual review.

## Helper
```bash
python3 skills/ast-grep/patterns.py  # ast grep helper
```

## Related Skills
- `grep_tool` — text-level search
- `search-replace` — pattern find/replace
- `code-review-workflow` — full review pipeline
- `bug_investigation` — structural pattern search for bugs
- `gitcrit` — git commit critique
- `debug` — structural search for debugging
- `refactor` — structural search/replace
- `debug` — interactive debugging
- `pyprep` — Python analysis tools
- `review` — detailed code review
