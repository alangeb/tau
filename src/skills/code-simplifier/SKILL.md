---
name: code-simplifier
description: "Reduce complexity — simplify nested conditionals, eliminate redundancy, consolidate logic without changing behavior (also load: code-review-workflow, refactor, pyprep, caveman)"
keywords: cyclomatic complexity reduction, conditional flattening, redundancy elimination, logic consolidation, nested structure simplification
category: development
---

# code-simplifier

## When
"simplify code" | "refactor" | "clean up" | "improve readability" | "reduce complexity" | "code review" | "review code"

## Rules
- **Preserve functionality** — behavior unchanged
- Reduce nesting, eliminate redundancy, consolidate logic
- Apply project standards (AGENT.md)
- No oversimplification hurting readability

## Helper
```bash
python3 skills/code-simplifier/simplify.py <file.py>  # Complexity analysis + suggestions
```

## Related Skills
- `code-review-workflow` — full review pipeline
- `python_best_practices` — linting/formatting
- `review` — detailed code review
- `caveman` — concise writing style
- `gitcrit` — git commit critique uses simplifier for complexity
- `refactor` — larger-scale restructuring
