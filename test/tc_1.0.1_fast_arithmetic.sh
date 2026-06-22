#!/bin/bash
# @group: 1
# @name: fast_arithmetic
# @tags: fast
# @timeout: 60
# @description: Test basic arithmetic calculation using bash tool

# @lines: 38

# @count: 1/4

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=0
export TEST_INDEX=1
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

# Setup - pass the actual test file path, not $0 (which is ./run when sourced)
setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_1.0.1_fast_arithmetic"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Lets do some basic math together. Let X be 37" "Now calculate X+42 and assign to X" "Now calculate X*13 and assign to X" "What is X (answer only plain number, no punctuation)?")
if expect_contains "1027" "$result" "Result should be 1027" "$TEST_NAME"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

# Cleanup
cleanup_test "$BASH_SOURCE"

# Archive failure if test failed
if [[ "$TEST_RESULT" == "FAIL" ]]; then
    archive_failure "$TEST_NAME" "$TEST_OUTPUT_DIR" "$output_file" "" ""
fi
