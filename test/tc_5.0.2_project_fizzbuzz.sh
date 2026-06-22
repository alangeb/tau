#!/bin/bash
# @group: 5
# @name: project_fizzbuzz
# @tags: slow
# @timeout: 180
# @description: Test FizzBuzz by running the program

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=5
export TEST_SUBGROUP=0
export TEST_INDEX=2
export TEST_TAGS=("slow")
export TEST_TIMEOUT=180

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_5.0.2_project_fizzbuzz"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Ask agent to write FizzBuzz program to file
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "write a FizzBuzz program that prints numbers 1-15 to 'fizzbuzz.py'")

# Check side effect: file exists
if ! expect_file_exists "fizzbuzz.py" "FizzBuzz program created" "$TEST_NAME"; then
    TEST_RESULT="FAIL"
    end_time=$(date +%s.%N)
    TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")
    cleanup_test "$BASH_SOURCE"
    exit 0
fi

# Run the program and capture output
program_output=$(python3 fizzbuzz.py 2>&1)

# Verify expected output
pass=1
echo "$program_output" | grep -q "Fizz" || pass=0
echo "$program_output" | grep -q "Buzz" || pass=0
echo "$program_output" | grep -q "14" || pass=0  # Should include numbers up to 15

# Verify correct FizzBuzz behavior (line 15 should be "FizzBuzz")
fizzbuzz_line=$(echo "$program_output" | tail -1 | tr -d '[:space:]')
if [[ "$fizzbuzz_line" == "FizzBuzz" ]]; then
    : # Good
else
    pass=0
fi

if [[ $pass -eq 1 ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
