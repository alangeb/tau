---
category: development
description: "Write pytest tests and unittest patterns, fixtures, coverage — pytest configuration, parametrize, mock (also load: tau_testsuite, debug, pyprep, tauskillmaintenance)"
keywords: pytest, test writing, unit test, test fixture, test coverage, parametrize, mock, assert pattern, test configuration, conftest
name: testing
---

# Testing

## When
"write test" | "pytest" | "unit test" | "test coverage" | "test fixture" | "conftest" | "test pattern" | "mock" | "parametrize"

## Pytest Patterns
```python
# Parametrize
@pytest.mark.parametrize("input,expected", [(1,2), (3,4)])
def test_calc(input, expected):
    assert calc(input) == expected

# Fixture
@pytest.fixture
def tmp_project(tmp_path):
    (tmp_path / "test.py").write_text("x=1")
    return tmp_path

# Mock
from unittest.mock import patch
def test_api():
    with patch("module.func") as m:
        m.return_value = "ok"
```

## Tau Test Structure
- `tests/unit/` — fast, no network
- `tests/integration/` — require setup
- `tests/sanity/` — regression, run after every change
- `conftest.py` at root + per-directory

## Run
```bash
pytest tests/ -x -v --tb=short
pytest tests/ --cov=tau --cov-report=term-missing
pytest tests/ -k "keyword"  # filter
```

## Helper
`python3 skills/testing/test_gen.py <function_name>` — generate test scaffold

## Related Skills
- `tau_testsuite` — Run tau test suite
- `debug` — Fix test failures
- `pyprep` — Understand code under test
- `code-review-workflow` — Review test quality
- `tauskillmaintenance` — Skill quality audit and maintenance
