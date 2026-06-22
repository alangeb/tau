#!/bin/bash
# @group: 1
# @name: fast_file_create
# @tags: fast
# @timeout: 60
# @description: Test simple file creation

# @lines: 43

# @count: 2/4

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=0
export TEST_INDEX=2
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_1.0.2_fast_file_create"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

test_file="./hello.txt"
rm -f $test_file
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create file '$test_file' with content 'Hello World!'")
pass=1
expect_file_exists "$test_file" "File was created" "$TEST_NAME" || pass=0
content=$(cat "$test_file")
expect_equal "$content" "Hello World!" "Content matches exactly" "$TEST_NAME" || pass=0
TEST_RESULT="PASS"
if [[ $pass -ne 1 ]]; then
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
