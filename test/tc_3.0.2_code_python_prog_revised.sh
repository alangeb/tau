#!/bin/bash
# @group: 3
# @name: code_python_prog_revised
# @tags: slow
# @timeout: 120
# @description: Test Python program creation and execution with robust validation

# @lines: 45

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

TEST_NAME="tc_3.0.2_code_python_prog_revised"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Create a Python program with main function that prints "Hello World!"
prog_file="./hello_world.py"
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create file '$prog_file' with content 'def main():\n    print(\"Hello World!\")\n\nif __name__ == \"__main__\":\n    main()'")

# Verify file was created (side effect) - use absolute path to avoid issues
abs_prog_file="$TEST_OUTPUT_DIR/$prog_file"
if [[ -f "$abs_prog_file" ]]; then
    # Execute the Python program and capture its output using python3
    python_result=$(python3 "$abs_prog_file" 2>&1)
    exit_code=$?
    
    # Verify execution completed without error
    if [[ $exit_code -eq 0 ]]; then
        # Check that output contains expected text (side effect validation)
        if expect_contains "Hello World!" "$python_result" "Python program output contains expected text" "$TEST_NAME"; then
            TEST_RESULT="PASS"
        else
            TEST_RESULT="FAIL"
        fi
    else
        TEST_RESULT="FAIL"
    fi
else
    # File doesn't exist - test fails
    expect_file_exists "$prog_file" "Python program file was created" "$TEST_NAME" || exit 1
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"