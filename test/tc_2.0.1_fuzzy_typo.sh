#!/bin/bash
# @group: 2
# @name: fuzzy_typo
# @tags: medium
# @timeout: 90
# @description: Test that fuzzy matching suggests 'file_read' for 'file_rade'

# @lines: 50

# @count: 5/7

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=1
export TEST_TAGS=("medium")
export TEST_TIMEOUT=90

# Setup - pass the actual test file path, not $0 (which is ./run when sourced)
setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.1_fuzzy_typo"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Create a test file first
echo "test file for fuzzy matching" > test_fuzzy_file.txt

# Use typo 'file_rade' - should get suggestion for 'file_read' and succeed
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "file_rade test_fuzzy_file.txt")
if expect_contains "test file for fuzzy matching" "$result" "Fuzzy matching works: 'file_rade' → 'file_read'" "$TEST_NAME"; then
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
