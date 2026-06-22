#!/bin/bash
# @group: 5
# @name: project_debug
# @tags: slow
# @timeout: 180
# @description: Test debugging and fixing buggy code

# @lines: 39

# @count: 1/4

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=5
export TEST_SUBGROUP=0
export TEST_INDEX=3
export TEST_TAGS=("slow")
export TEST_TIMEOUT=180

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_5.0.3_project_debug"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

buggy_file="./buggy.py"
create_test_file "$buggy_file" "def add(a, b):\n    return a - b  # Bug: should be +\n\nprint(add(5, 3))"
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "fix the bug in '$buggy_file' and run it")
if expect_contains "8" "$result" "Fixed code should output 8" "$TEST_NAME"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
