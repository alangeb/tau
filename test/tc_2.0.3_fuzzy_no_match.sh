#!/bin/bash
# @group: 2
# @name: fuzzy_no_match
# @tags: fast
# @timeout: 60
# @description: Test that unknown tool 'xyz123' gives clean error with no false suggestions

# @lines: 50

# @count: 7/7

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=3
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

# Setup - pass the actual test file path, not $0 (which is ./run when sourced)
setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.3_fuzzy_no_match"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Use completely unknown tool 'xyz123' - should get clean error without false suggestions
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "xyz123 --help")
# Check that the error mentions 'xyz123 not found' and does NOT suggest unrelated tools
if expect_contains "xyz123" "$result" "Error message should mention 'xyz123'" "$TEST_NAME"; then
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
