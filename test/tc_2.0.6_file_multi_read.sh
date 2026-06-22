#!/bin/bash
# @group: 2
# @name: file_multi_read
# @tags: slow
# @timeout: 120
# @description: Test multi-file read via side effects

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=6
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.6_file_multi_read"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

test_dir="./multi_read"
mkdir -p "$test_dir"

# Create input files
echo "First file content" > "$test_dir/file1.txt"
echo "Second file content" > "$test_dir/file2.txt"
echo "Third file content" > "$test_dir/file3.txt"

# Ask agent to read files and write results to output files
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "read '$test_dir/file1.txt' '$test_dir/file2.txt' '$test_dir/file3.txt' output to '$test_dir/output1.txt' '$test_dir/output2.txt' '$test_dir/output3.txt'")

# Check side effects: output files exist with correct content
pass=1
expect_file_contains "$test_dir/output1.txt" "First file content" "Output1 has file1 content" "$TEST_NAME" || pass=0
expect_file_contains "$test_dir/output2.txt" "Second file content" "Output2 has file2 content" "$TEST_NAME" || pass=0
expect_file_contains "$test_dir/output3.txt" "Third file content" "Output3 has file3 content" "$TEST_NAME" || pass=0

if [[ $pass -eq 1 ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
