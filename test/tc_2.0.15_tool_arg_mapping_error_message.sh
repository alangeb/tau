#!/bin/bash
# @group: 2
# @name: tool_arg_mapping_error_message
# @tags: fast validation
# @timeout: 60
# @description: Test error message format for unknown CLI-style parameters

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=15
export TEST_TAGS=("fast" "validation")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.15_tool_arg_mapping_error_message"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Send a command that would trigger CLI-style parameter usage
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Try to search for 'test' with -n flag")

# Check if agent handles CLI-style flag gracefully (auto-correction or explanation)
# This is the expected/happy path - agent understands -n means line numbers
if echo "$result" | grep -qi "line.*number\|output_format.*lines\|equivalent.*-n"; then
    log_pass "CLI flag handled gracefully (auto-corrected or explained)"
    TEST_RESULT="PASS"
elif expect_contains "'-n'" "$result" "CLI flag shown in error" "$TEST_NAME"; then
    # Alternative: agent shows error with CLI→parameter mapping
    if expect_contains "recursive" "$result" "Parameter mapping shown" "$TEST_NAME"; then
        log_pass "Error message contains CLI → parameter mapping"
        TEST_RESULT="PASS"
    else
        log_fail "Missing parameter mapping in error message"
        TEST_RESULT="FAIL"
    fi
else
    # Neither graceful handling nor helpful error
    log_fail "CLI flag not properly handled or explained"
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
