---
category: development
description: "Run tau test suite, sanity check, execute regression tests, verify everything works (also load: background, dependency_management, tau_audit, test-suite-monitor, testing)"
keywords: tau test suite, sanity check, regression tests, test execution, test verification, tau testing
name: tau_testsuite
---

# Test Suite

## When
"create test" | "test suite" | "write test case" | "test structure" | "test helpers" | "test automation" | "test" | "testing" | "run tests" | "run test suite"

## Quick Start
```bash
cd $HOME/tau/test && ./run           # All tests
cd $HOME/tau/test && ./run tc_1.0.1  # Specific test
cd $HOME/tau/test && ./run tc_1.*    # Group 1
```

## Test Groups
`tc_1.X.X` Basic commands | `tc_2.X.X` File ops | `tc_3.X.X` Python code gen | `tc_4.X.X` Context management | `tc_5.X.X` Project-level | `tc_6.X.X` Edge cases | `tc_7.X.X` External web | `tc_8.X.X` A2A protocol | `tc_9.X.X` Tmux background | `tc_10.X.X` Fast A2A | `tc_11.X.X` Additional

## Helpers (sourced via `func`)
`expect_equal exp act msg name` Exact | `expect_contains needle haystack msg name` Substring | `expect_not_contains needle haystack msg name` Not found | `expect_file_exists file msg name` Exists | `expect_not_file_exists file msg name` Deleted | `expect_file_contains file needle msg name` Content | `expect_numeric exp act op msg name` Numeric (eq/gt/lt) | `expect_numeric_range label haystack min msg name` Range

## Critical Rules

### DO NOT Invert Helper Results
`expect_*` handles PASS/FAIL internally. Trust return value.
```bash
# CORRECT: if expect_file_exists "output.txt" "File created" "$TEST_NAME"; then TEST_RESULT="PASS"; else TEST_RESULT="FAIL"; fi
# WRONG: if ! expect_file_exists "output.txt" ...
```

### Prefer Side Effects Over Output Parsing
✓ File created → `expect_file_exists` | ✓ File modified → `expect_file_contains`
✗ Testing for own input verbatim (circular)

### Single Responsibility
One thing per test. Name: `tc_<major>.<minor>.<idx>_<name>.sh`

## Test Template
```bash
setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"
TEST_NAME="tc_X.Y.Z_name"
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "instruction")
expect_file_exists "output.txt" "File created" "$TEST_NAME"
TEST_RESULT="PASS"
cleanup_test "$BASH_SOURCE"
```

## A2A Fast Tests
```bash
python "$DUT_PATH" --keep-alive > "$output_file" 2>&1 &
AGENT_PID=$!
timeout 10 sh -c 'until [ -S "/tmp/taua2a-${AGENT_PID}.sock" ]; do sleep 0.1; done'
result=$(python "$DUT_PATH" --pid "$AGENT_PID" "query" 2>&1)
cleanup_a2a_agent "$AGENT_PID"
```

## Checklist
- [ ] Required header (`@group`, `@name`, `@tags`, `@timeout`, `@description`)
- [ ] Uses `setup_test` → `run_tool_capture` → assertions → `cleanup_test`
- [ ] Prefers side effects over output parsing; does NOT invert `expect_*` logic
- [ ] Single responsibility; output dir has all expected files
- [ ] `status.json` correct structure; runs locally without manual setup

## Helper
```bash
source skills/tau_testsuite/test_runner.sh
```

## Related Skills
- `test-suite-monitor` — Background test monitoring workflow
- `background` — Tmux session management
- `dependency_management` — Test dependencies
- `tmux_monitoring` — Session polling
- `tau_audit` — audit log analysis for test results
- `testing` — Write pytest tests, fixtures, coverage
- `release_management` — Version bumping, changelog
