---
name: code-simplifier
description: Simplify code for clarity, consistency, maintainability — preserve functionality. Simplify code, refactor, clean code, reduce complexity (also load: code-review-workflow, review, python_best_practices)
category: coding
keywords: simplify, refactor, clean code, reduce complexity, improve readability, make clearer, code clarity
---

# Code Simplifier

## When
"simplify code", "refactor", "clean up code", "improve readability", "make code clearer"

## Rules
- **Preserve functionality** — never change behavior
- **Apply project standards** — see AGENT.md
- Reduce nesting, eliminate redundancy, consolidate logic
- No oversimplification that hurts readability

## Avoid
- Nested ternaries → switch or if/else chains
- Dense one-liners → clarity over brevity
- Overly clever solutions
- Removing helpful abstractions

## Process
1. Identify target sections
2. Apply simplifications
3. Verify functionality unchanged
4. Document significant changes only

## Helper
```bash
python3 skills/code-simplifier/simplify.py <file.py>  # Complexity analysis + suggestions
```

## Related Skills
- `code-review-workflow` — complete review pipeline
- `review` — detailed code review process
- `caveman` — concise writing style
- `python_best_practices` — linting/formatting
