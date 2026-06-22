# Test Suite

**Location**: `$HOME/tau/test/`

## Quick Start

```bash
cd $HOME/tau/test
./run              # Run all tests
./run tc_1.0.1     # Run specific test
./run tc_1.*       # Run group 1 tests
./run --verbose    # Verbose output
./run --fail-only  # Show failures only
```

## Structure

```
test/
├── env              # Environment config (API_URL, paths) — shell script
├── func             # Helper functions (assertions, logging) — shell script
├── run              # Test runner script
├── tc_*.sh          # Test files (tc_<major>.<minor>.<idx>_<name>)
├── output/          # Test results (per-test directories)
├── IMPLEMENTATION_STATUS.md  # Implementation status tracking
└── TODO.md          # Pending test items
```

## Test Groups

| Group | Purpose |
|-------|---------|
| 1 | Basic commands (aliases, stdin, Ctrl-C, commands) |
| 2 | File operations (edit, list, create, overwrite, grep, head, wc, fuzzy matching) |
| 3 | Python code generation (exec, program, info, loop, variables, math) |
| 4 | Context management (persist, compress, multiturn) |
| 5 | Project-level tests (multi-file, fizzbuzz, debug, e2e, pyscan variants) |
| 6 | Edge cases (errors, special chars, tool call patterns) |
| 7 | External web |
| 8 | A2A protocol (basic, context, card, list, timeout, no agent) |
| 9 | Tmux sessions (new, ls, kill, exec, send keys, capture, tail, env, vi/nano, parallel, isolation, communication, cleanup, chaining, timing, validation) |
| 10 | **Fast test suites via A2A** (sanity, context, subagent, commands, multistep) |
| 11 | Python commands (discovery, delegate, unknown, A2A) |

## Test Anatomy

Each test follows **SETUP → EXECUTE → VALIDATE → CLEANUP**:

1. **SETUP**: Initialize, create test artifacts
2. **EXECUTE**: Run agent via `run_tool_capture()` or A2A query
3. **VALIDATE**: Check results with `expect_*()` helpers
4. **CLEANUP**: Restore state via `cleanup_test()`

## Helper Functions

### Assertions (return 0=PASS, 1=FAIL)
- `expect_equal expected actual msg testname`
- `expect_contains needle haystack msg testname`
- `expect_not_contains needle haystack msg testname`
- `expect_file_exists file msg testname`
- `expect_not_file_exists file msg testname`
- `expect_file_contains file needle msg testname`
- `expect_numeric exp act op msg testname`
- `expect_numeric_range exp act min max op msg testname`

### Helpers
- `setup_test test_file` — Initialize test artifacts
- `cleanup_test` — Restore state
- `setup_a2a_socket` — Prepare A2A socket for fast tests
- `cleanup_a2a_agent` — Clean up A2A agent session
- `create_test_file file content` — Write file
- `run_tool_capture output_file timeout input...` — Run agent
- `log_pass log_fail log_skip log_info log_warn log_error` — Colored logging

## ⚠️ Critical: Don't Invert Helpers

The `expect_*()` helpers already print PASS/FAIL and return 0/1.

**DO:**
```bash
if expect_file_exists "out.txt" "File exists" "$TEST_NAME"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi
```

**DON'T:**
```bash
if ! expect_file_exists "out.txt" "File deleted" "$TEST_NAME"; then
    TEST_RESULT="PASS"  # Wrong: visual says PASS but actually FAILED
fi
```

## Output Structure

Each test creates `$OUTPUT_DIR/<name>/`:
- `status.json` - Metadata
- `tool_output.txt` - Full agent output
- `input.log` - User inputs
- `assertions.log` - JSON assertion results
- `log.txt` - Test framework log

## Test Requirements

Header required in each test file:
```bash
#!/bin/bash
# @group: X
# @name: test_name
# @tags: fast|slow|critical
# @timeout: 60
# @description: What this test verifies
```

## Key Principles

1. **Prefer side effects** - Test file existence/content, not output text
2. **Test LLM-Produced content** - LLM confirmation, not your input
3. **Single responsibility** - One thing per test

## Failure Archiving

Failed tests archived to `~/.local/tau/logerror/`:
- `.meta.json`, `.env.json` - Metadata
- `.input.json`, `.assertions.json` - Test data
- `.agent_output.txt` - Full output
- `.system.txt` - System info

## Fast Test Suites via A2A

### Intent

For **fast iteration testing**, run multiple test scenarios against a **single agent instance** using A2A (agent-to-agent) protocol. This avoids the overhead of starting/stopping the agent for each test.

**Traditional approach**: Start agent → Run 1 test → Stop agent (repeated)
**Fast A2A approach**: Start agent once → Run N tests via A2A → Stop agent

### Test Cases

#### `tc_10.0.1_a2a_sanity` (Group 10.0.1)
**Purpose**: Verify A2A communication is working at a basic level.

**What it does**:
1. Starts agent with `--keep-alive` (persistent session)
2. Waits for A2A socket to appear
3. Sends a simple arithmetic query via A2A (e.g., "How much is 112233*2?")
4. Validates the response contains the correct result (224466)
5. Cleans up agent session

**How A2A works**:
- The A2A protocol returns a JSON-like response with `Query:`, `Response:`, and `Context length:`
- Agent commands that go through the assistant flow (like arithmetic) return the LLM response
- Agent commands that print directly (like `/help`, `/toolsjson`) do NOT populate the A2A response

**Use case**: Quick sanity check that A2A infrastructure is functional before running larger test suites.

#### `tc_10.0.2_a2a_test_suite` (Group 10.0.2)
**Purpose**: Batch test suite for A2A tests, gradually expanding capabilities.

**Current test scenarios**:
1. Basic arithmetic: "How much is 112233*2?" → validates "224466"
2. Context preservation: "Remember: test_value=999" → validates context stores "999"
3. Context recall: "What is test_value?" → validates context returns "999"
4. Context update: "Update: test_value=777" → validates context updates to "777"
5. Post-update recall: "What is test_value now?" → validates context returns "777"
6. Calculation using context: "Calculate test_value + 222, answer only the number" → validates "999" (777 + 222)
7. Undo functionality: "/undo" followed by "What is test_value after undo?" → validates context reverts to "999"

**Development notes**:
- This test file is designed for gradual expansion
- New tests are added sequentially as they are developed
- Each test uses `expect_*` helpers with `|| ALL_PASSED=false` for aggregation
- Tests are validated by running `./run tc_10.0.2` after adding each test
- A2A response format: `Query: <query>\nResponse:\n<llm_response>\nContext length: <n>`
- Arithmetic and assistant-flow queries return LLM response
- Agent commands that print directly (like `/help`, `/toolsjson`) don't populate A2A response
- Use `/undo` for testing context restoration capabilities

**Adding new tests**:
```bash
# Add after TEST 7, before # ============================================================================
# Test N: <description>
result=$(python "$DUT_PATH" --pid "$AGENT_PID" "query" 2>&1) || true
result_clean=$(echo "$result" | sed 's/\x1b\[[0-9;]*m//g')
expect_contains "expected" "$result_clean" "validation message" "$TEST_NAME" || ALL_PASSED=false
```

**Key differences from tc_10.0.1**:
- Tests multiple scenarios in sequence (not just one)
- Uses `expect_*` helpers for validation (don't invert them!)
- Aggregates results with `ALL_PASSED` flag
- Designed for incremental test development
- Includes stateful tests (context preservation, update, recall, undo)

**Use case**: Development feedback loop - verify all core capabilities before committing; regression testing.

### Performance Benefits

- **No agent startup time** (5-10s saved per test)
- **Shared context** (cached models/states reused)
- **Parallelizable** (multiple agents can run concurrently for different test batches)

### When to Use A2A Fast Tests

| Scenario | Approach |
|----------|----------|
| Quick sanity check | `tc_10.0.1` |
| Multiple scenarios, one agent | `tc_10.0.2` |
| Single complex scenario | Traditional `tc_1-9.X.X` |
| Stateful test sequences | Traditional `tc_1-9.X.X` |

### Reference

- **Skill**: `src/skills/tau_testsuite.md` — Comprehensive testing guide with full templates, A2A testing patterns, and helper reference. Use the `skill` tool to load it.
- **Sanity Suite**: `bash sanity.sh` (from project root) — End-to-end tests requiring an LLM endpoint (~100s, gold standard). Covers CLI, positional args, tool calling, fork functionality, and context persistence.
- **Unit Tests**: `cd src && pytest` — 23+ test files covering context, LLM pipeline, tools, delegation, A2A, config, and more.

## Debugging Failures

1. **Check test output**: `cat output/<testname>/tool_output.txt` for full agent output
2. **Check assertions**: `cat output/<testname>/assertions.log` for assertion results
3. **Check logs**: `cat output/<testname>/log.txt` for framework logs
4. **Re-run single test**: `./run tc_X.Y.Z` to isolate the failure
5. **Verbose mode**: `./run --verbose tc_X.Y.Z` for detailed output
6. **Check env**: Verify `env/` config (API_URL, paths) is correct for your setup
7. **Manual test**: Reproduce the test scenario manually with `python ../src/tau.py "your test input"`
