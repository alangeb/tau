#!/bin/bash
# @group: 2
# @name: file_wc
# @tags: slow
# @timeout: 120
# @description: Test wc tool

# @lines: 41

# @count: 1/10

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=10
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.10_file_wc"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

test_file="./wc_test.txt"
create_test_file "$test_file" "Hello World
This is a test file
With multiple lines"
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "wc -l '$test_file'")
if expect_numeric "3" "3" "eq" "Should have 3 lines" "$TEST_NAME"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
