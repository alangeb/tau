#!/bin/bash
# @group: 4
# @name: context_compress
# @tags: slow
# @timeout: 120
# @description: Test context compression

# @lines: 38

# @count: 2/3

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=4
export TEST_SUBGROUP=0
export TEST_INDEX=2
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_4.0.2_context_compress"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Test that agent can remember and confirm within single conversation
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Remember: context_test_value=123. Confirm the value.")
if expect_contains "123" "$result" "Context value should be preserved" "$TEST_NAME"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
