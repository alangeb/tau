#!/bin/bash
# @group: 4
# @name: context_persist
# @tags: slow
# @timeout: 120
# @description: Test context persistence within single session

# @lines: 38

# @count: 1/3

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=4
export TEST_SUBGROUP=0
export TEST_INDEX=1
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_4.0.1_context_persist"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Test that agent can remember within a single call (multi-turn conversation)
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Remember: X=40+1."  "Now tell me the value of X.")
if expect_contains "41" "$result" "Agent should remember X=41 in same conversation" "$TEST_NAME"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
