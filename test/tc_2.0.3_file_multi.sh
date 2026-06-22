#!/bin/bash
# @group: 2
# @name: file_multi
# @tags: slow
# @timeout: 120
# @description: Test multi-file read and write via side effects

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=3
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.3_file_multi"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

test_dir="./multi_test"
mkdir -p "$test_dir"

# Create two files with numbers
echo "X=111111" > "$test_dir/fileA.txt"
echo "Y=222222" > "$test_dir/fileB.txt"

# Ask agent to read both files and write sum to third file
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" \
    "read file '$test_dir/fileA.txt'" \
    "read file '$test_dir/fileB.txt'" \
    "based on the information from the 2 files read, calculate X+Y, write result of X+Y into file '$test_dir/fileC.txt'" \
    )

# Check side effect: fileC contains only 333333
if expect_file_contains "$test_dir/fileC.txt" "333333" "File C contains sum 333333" "$TEST_NAME"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
