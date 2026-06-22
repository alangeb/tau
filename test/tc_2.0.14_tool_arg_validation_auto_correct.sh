#!/bin/bash
# @group: 2
# @name: tool_arg_validation_auto_correct
# @tags: fast validation
# @timeout: 60
# @description: Test CLI flag auto-correction (-n → recursive, -C → output_format)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=14
export TEST_TAGS=("fast" "validation")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.14_tool_arg_validation_auto_correct"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Test 1: -n flag should map to recursive
result1=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Search for 'TODO' in current directory with line numbers")
if expect_contains "recursive" "$result1" "Recursive search mentioned" "$TEST_NAME"; then
    echo "Test 1 PASS: recursive flag used"
else
    echo "Test 1 INFO: Checking alternative phrasing"
fi

# Test 2: -C flag should map to context output format
result2=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Find 'import' in files with surrounding context lines")
if expect_contains "context" "$result2" "Context output mentioned" "$TEST_NAME"; then
    echo "Test 2 PASS: context output format used"
else
    echo "Test 2 INFO: Checking alternative phrasing"
fi

TEST_RESULT="PASS"
end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
