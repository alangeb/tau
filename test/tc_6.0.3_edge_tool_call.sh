#!/bin/bash
# @group: 6
# @name: edge_tool_call
# @tags: slow
# @timeout: 120
# @description: Test tool call structure verification

# @lines: 37

# @count: 1/3

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=6
export TEST_SUBGROUP=0
export TEST_INDEX=3
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_6.0.3_edge_tool_call"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "use bash to run: echo 'test'")
if expect_contains "test" "$result" "Should execute bash command" "$TEST_NAME"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
