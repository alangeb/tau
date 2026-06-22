#!/bin/bash
# @group: 1
# @name: alias_redirect_read_file
# @tags: fast
# @timeout: 60
# @description: Test that 'read_file' alias redirects to file_read

# @lines: 44

# @count: 4/7

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=0
export TEST_INDEX=4
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

# Setup - pass the actual test file path, not $0 (which is ./run when sourced)
setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_1.0.4_alias_redirect_read_file"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Create a test file first
echo "This is a test file for read_file alias" > test_readfile_alias.txt

# Use 'read_file' instead of 'file_read' - should redirect automatically
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "read_file test_readfile_alias.txt")
if expect_contains "test file for read_file alias" "$result" "Alias redirect works: 'read_file' → 'file_read'" "$TEST_NAME"; then
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
