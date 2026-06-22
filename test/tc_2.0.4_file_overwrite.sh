#!/bin/bash
# @group: 2
# @name: file_overwrite
# @tags: slow
# @timeout: 120
# @description: Test file overwrite via side effects only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=4
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.4_file_overwrite"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

test_file="./overwrite_test.txt"
create_test_file "$test_file" "Original content"

# Ask agent to overwrite file
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create file '$test_file' with content 'Overwritten content'")

# Check side effects only: new content exists, old content gone
if expect_file_contains "$test_file" "Overwritten content" "File has new content" "$TEST_NAME"; then
    if expect_not_contains "$test_file" "Original content" "Old content removed" "$TEST_NAME"; then
        TEST_RESULT="PASS"
    else
        TEST_RESULT="FAIL"
    fi
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
