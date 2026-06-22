#!/bin/bash
# @group: 1
# @name: alias_redirect_list
# @tags: fast
# @timeout: 60
# @description: Test that 'list' alias redirects to run_shell_command

# @lines: 44

# @count: 2/7

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=0
export TEST_INDEX=2
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

# Setup - pass the actual test file path, not $0 (which is ./run when sourced)
setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_1.0.2_alias_redirect_list"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Create a test file first
echo "test content" > test_list_file.txt

# Use 'list' instead of 'run_shell_command' - should redirect automatically
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "list .")
if expect_contains "test_list_file.txt" "$result" "Alias redirect works: 'list' → 'run_shell_command'" "$TEST_NAME"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

# Cleanup
cleanup_test "$BASH_SOURCE"

# Archive failure if test failed
if [[ "$TEST_RESULT" == "FAIL" ]]; then
    archive_failure "$TEST_NAME" "$TEST_OUTPUT_DIR" "$output_file" "" ""
fi
