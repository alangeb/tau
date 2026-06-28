---
name: documentation
description: Documentation patterns — docstrings, changelog format. Write docs, documentation, changelog, release notes, docstrings (also load: _taudoc, readme_template)
category: documentation
keywords: documentation, docstring, changelog, release notes, write docs
---

# Documentation

## When
"write docstring", "document code", "changelog", "release notes", "write docs", "docstrings"

## Docstring Format (Google style)
```python
def function(arg1, arg2):
    """Brief description.

    Args:
        arg1: Description
        arg2: Description

    Returns:
        Description

    Raises:
        ExceptionType: When condition
    """
```

## Changelog Format
```markdown
## [Version] - YYYY-MM-DD

### Added
- Feature

### Changed
- Change

### Fixed
- Bug fix

### Removed
- Deprecated
```

## Rules
- Docstrings on all public functions/classes
- Brief one-line summary first
- Args/Returns/Raises for non-trivial functions
- Changelog: semantic sections only

## Helper

```bash
python3 skills/documentation/doc_helper.py  # documentation helper
```
## Related Skills
- `_taudoc` — project documentation structure
- `readme_template` — README documentation
- `code-review-workflow` — review documentation quality

- `skill_template` — Create new skill or modify existing skills. Create skill