#!/bin/bash
# @group: 2
# @name: file_grep
# @tags: slow
# @timeout: 120
# @description: Test grep via side effects

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=8
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.8_file_grep"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

test_file="./grep_test.txt"
create_test_file "$test_file" "Line 1: apple
Line 2: banana
Line 3: apple pie
Line 4: cherry
Line 5: applejack"

output_file="./grep_output.txt"

# Ask agent to grep and write results to file
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "grep 'apple' '$test_file' output to '$output_file'")

# Check side effect: output file exists with apple matches
if expect_file_exists "$output_file" "Grep output file created" "$TEST_NAME"; then
    if expect_file_contains "$output_file" "apple" "Output contains apple matches" "$TEST_NAME"; then
        # Verify we got at least 3 matches (apple, apple pie, applejack)
        match_count=$(grep -c "apple" "$output_file" 2>/dev/null || echo "0")
        if [[ "$match_count" -ge 3 ]]; then
            TEST_RESULT="PASS"
        else
            TEST_RESULT="FAIL"
        fi
    else
        TEST_RESULT="FAIL"
    fi
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
