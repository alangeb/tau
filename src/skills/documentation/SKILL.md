---
name: documentation
description: "Documentation patterns — docstrings, changelog, release notes. Write docs, technical writing (also load: _taudoc, image, readme_template, caveman, code-review-workflow, skill_template, wiki)"
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
- `caveman` — write concise docs
- `code-review-workflow` — review documentation quality
- `skill_template` — skill creation format
- `wiki` — knowledge storage and retrieval
