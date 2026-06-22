#!/bin/bash
# @group: 3
# @name: code_python_prog
# @tags: slow
# @timeout: 120
# @description: Test Python program creation

# @lines: 41

# @count: 1/6

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=3
export TEST_SUBGROUP=0
export TEST_INDEX=2
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_3.0.2_code_python_prog"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

prog_file="./test_program.py"
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create file '$prog_file' with content 'def hello():\n    print(\"Hello from Python!\")\n\nhello()'")
pass=1
expect_contains "Hello from Python" "$result" "Program creation confirmation" "$TEST_NAME" || pass=0
expect_file_exists "$prog_file" "Python program was created" "$TEST_NAME" || pass=0
TEST_RESULT="PASS"
if [[ $pass -ne 1 ]]; then
    TEST_RESULT="FAIL"
fi
end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"