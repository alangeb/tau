---
description: "Refactor and restructure code safely, clean up — rename symbols, extract methods, move code, inline, ast-grep (also load: ast-grep, code-review-workflow, python_best_practices, review, code-simplifier, pyprep, search-replace)"
keywords: symbol rename across files, method extraction, module relocation, variable inlining, ast-grep structural transformation
name: refactor
category: development
---

# Refactor

## When
"refactor code" | "rename function" | "extract method" | "restructure" | "reorganize code" | "move code" | "code review" | "review code"

## Rules
- Preserve functionality — behavior unchanged
- Run tests before and after
- Small incremental changes — one refactoring per commit
- `ast-grep` for structural search/replace
- `grep_tool` for text-based search/replace
- Verify with `git-verify` diff review

## Common Refactorings
| Type | Tool | Pattern |
|------|------|---------|
| Rename | `ast-grep` + `search-replace` | Symbol rename across files |
| Extract | `file_edit` | Extract function/method |
| Move | `file_edit` + `git` | Move code between files |
| Inline | `search-replace` | Inline variable/function |
| Split | `file_write` + `file_edit` | Split large file |
| Merge | `file_edit` | Merge small files |

## Sequence
1. `pyscan(compact=True)` — understand structure
2. `pygraph` — identify call relationships
3. `grep` — find all references
4. Apply changes (small, incremental)
5. `git diff` — review
6. Run tests — verify
7. `git commit` — save

## Helper
```bash
python3 skills/refactor/refactor_check.py <file.py>  # Impact analysis
```

## Related Skills
- `code-simplifier` — simplify code complexity
- `search-replace` — text substitution
- `ast-grep` — structural search/replace
- `code-review-workflow` — verify changes
- `git-verify` — diff review
- `pyprep` — Python analysis
- `git` — commit refactored changes
- `grep_tool` — trace call sites and execution paths
