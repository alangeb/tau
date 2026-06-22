#!/bin/bash
# @group: 2
# @name: file_edit_single
# @tags: slow
# @timeout: 120
# @description: Test single line file edit

# @lines: 41

# @count: 1/10

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=1
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.1_file_edit_single"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

test_file="./edit_test.txt"
create_test_file "$test_file" "Line 1: Original content
Line 2: More content
Line 3: Third line"
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "read '$test_file' change 'Line 2: More content' to 'Line 2: Modified content'")
if expect_file_contains "$test_file" "Line 2: Modified content" "File edited correctly" "$TEST_NAME"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
