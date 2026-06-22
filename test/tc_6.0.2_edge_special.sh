#!/bin/bash
# @group: 6
# @name: edge_special
# @tags: slow
# @timeout: 120
# @description: Test special characters handling

# @lines: 40

# @count: 1/3

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=6
export TEST_SUBGROUP=0
export TEST_INDEX=2
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_6.0.2_edge_special"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create file './special.txt' with content 'Special chars: @#\$%^&*()!\\\"'")
pass=1
expect_contains "Special chars" "$result" "Should handle special characters" "$TEST_NAME" || pass=0
expect_file_exists "./special.txt" "Special chars file created" "$TEST_NAME" || pass=0
TEST_RESULT="PASS"
if [[ $pass -ne 1 ]]; then
    TEST_RESULT="FAIL"
fi
end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
