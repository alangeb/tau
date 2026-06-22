#!/bin/bash
# @group: 11
# @name: py_command_discovery
# @tags: fast
# @timeout: 60
# @description: Test .py command discovery and loading

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=11
export TEST_SUBGROUP=0
export TEST_INDEX=1
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_11.0.1_py_command_discovery"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# ============================================================================
# TEST 1: /help shows External Python Commands section
# ============================================================================

log_info "[COMM] /help"
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "/help")
result_clean=$(echo "$result" | sed 's/\x1b\[[0-9;]*m//g')

ALL_PASSED=true

if ! expect_contains "External Python Commands" "$result_clean" "Help shows External Python Commands section" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result_clean:0:500}"
    ALL_PASSED=false
fi

if ! expect_contains "delegate" "$result_clean" "Help shows delegate command" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result_clean:0:500}"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 2: /help shows External Markdown Commands section
# ============================================================================

if ! expect_contains "External Markdown Commands" "$result_clean" "Help shows External Markdown Commands section" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result_clean:0:500}"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 3: /help shows Built-in Commands section
# ============================================================================

if ! expect_contains "Built-in Commands" "$result_clean" "Help shows Built-in Commands section" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result_clean:0:500}"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 4: /commands shows three categories
# ============================================================================

log_info "[COMM] /commands"
result2=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "/commands")
result2_clean=$(echo "$result2" | sed 's/\x1b\[[0-9;]*m//g')

if ! expect_contains "Built-in Commands" "$result2_clean" "Commands shows Built-in Commands section" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result2_clean:0:500}"
    ALL_PASSED=false
fi

if ! expect_contains "External Python Commands" "$result2_clean" "Commands shows External Python Commands section" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result2_clean:0:500}"
    ALL_PASSED=false
fi

if ! expect_contains "External Markdown Commands" "$result2_clean" "Commands shows External Markdown Commands section" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result2_clean:0:500}"
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
