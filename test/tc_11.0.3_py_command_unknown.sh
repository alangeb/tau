#!/bin/bash
# @group: 11
# @name: py_command_unknown
# @tags: fast
# @timeout: 60
# @description: Test unknown command error handling

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=11
export TEST_SUBGROUP=0
export TEST_INDEX=3
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_11.0.3_py_command_unknown"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# ============================================================================
# TEST 1: Unknown command shows error
# ============================================================================

log_info "[COMM] /nonexistent_command_xyz"
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "/nonexistent_command_xyz")
result_clean=$(echo "$result" | sed 's/\x1b\[[0-9;]*m//g')

ALL_PASSED=true

if ! expect_contains "Unknown command" "$result_clean" "Unknown command shows error" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result_clean:0:500}"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 2: .md command still works (fallback)
# ============================================================================

log_info "[COMM] /recap"
result2=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "/recap")
result2_clean=$(echo "$result2" | sed 's/\x1b\[[0-9;]*m//g')

if ! expect_contains "recap" "$result2_clean" ".md command /recap still works" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result2_clean:0:500}"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 3: Built-in command still works
# ============================================================================

log_info "[COMM] /status"
result3=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "/status")
result3_clean=$(echo "$result3" | sed 's/\x1b\[[0-9;]*m//g')

if ! expect_contains "PID:" "$result3_clean" "Built-in /status still works" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result3_clean:0:500}"
    ALL_PASSED=false
fi

if [[ "$ALL_PASSED" == "true" ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
