#!/bin/bash
# @group: 2
# @name: file_create_delete
# @tags: slow
# @timeout: 120
# @description: Test file creation and deletion via side effects only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=5
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.5_file_delete"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

test_file="./delete_test.txt"

# Stage 1: Create file and verify side effect
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create file '$test_file' with content 'content to delete'")
if ! expect_file_exists "$test_file" "File should be created" "$TEST_NAME"; then
    TEST_RESULT="FAIL"
    end_time=$(date +%s.%N)
    TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")
    cleanup_test "$BASH_SOURCE"
    exit 0
fi

# Stage 2: Delete file and verify side effect only
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "delete file '$test_file'")
if expect_not_file_exists "$test_file" "File should be deleted" "$TEST_NAME"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
