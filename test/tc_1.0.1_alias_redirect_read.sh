#!/bin/bash
# @group: 1
# @name: alias_redirect_read
# @tags: fast
# @timeout: 60
# @description: Test that 'read' alias redirects to file_read

# @lines: 44

# @count: 1/7

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=0
export TEST_INDEX=1
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

# Setup - pass the actual test file path, not $0 (which is ./run when sourced)
setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_1.0.1_alias_redirect_read"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Create a test file first
echo "This is a test file for alias redirect" > test_alias_file.txt

# Use 'read' instead of 'file_read' - should redirect automatically
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "read test_alias_file.txt")
if expect_contains "test file for alias redirect" "$result" "Alias redirect works: 'read' → 'file_read'" "$TEST_NAME"; then
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
