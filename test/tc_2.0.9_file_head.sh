#!/bin/bash
# @group: 2
# @name: file_head
# @tags: slow
# @timeout: 120
# @description: Test head tool

# @lines: 56

# @count: 1/10

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=9
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.9_file_head"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

test_file="./head_test.txt"
create_test_file "$test_file" "Line 1
Line 2
Line 3
Line 4
Line 5
Line 6
Line 7
Line 8
Line 9
Line 10"
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "head -5 '$test_file'")
pass=1
expect_contains "Line 1" "$result" "Should contain Line 1" "$TEST_NAME" || pass=0
expect_contains "Line 5" "$result" "Should contain Line 5" "$TEST_NAME" || pass=0
# Only check for "Line 6" as a standalone line (not in log/metadata)
# Use word boundary to avoid false positives
if echo "$result" | grep -qE '^[[:space:]]*Line 6[[:space:]]*$'; then
    pass=0
fi
TEST_RESULT="PASS"
if [[ $pass -ne 1 ]]; then
    TEST_RESULT="FAIL"
fi
end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
