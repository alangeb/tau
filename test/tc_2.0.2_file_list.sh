#!/bin/bash
# @group: 2
# @name: file_list
# @tags: slow
# @timeout: 120
# @description: Test directory listing

# @lines: 46

# @count: 2/10

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=2
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.2_file_list"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

test_dir="./list_test"
mkdir -p "$test_dir"
echo "file1" > "$test_dir/file1.txt"
echo "file2" > "$test_dir/file2.txt"
echo "file3" > "$test_dir/file3.txt"
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "use bash to run: ls -la '$test_dir'")
pass=1
expect_contains "file1.txt" "$result" "Should list file1.txt" "$TEST_NAME" || pass=0
expect_contains "file2.txt" "$result" "Should list file2.txt" "$TEST_NAME" || pass=0
expect_contains "file3.txt" "$result" "Should list file3.txt" "$TEST_NAME" || pass=0
TEST_RESULT="PASS"
if [[ $pass -ne 1 ]]; then
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
