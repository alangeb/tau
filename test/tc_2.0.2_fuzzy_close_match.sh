#!/bin/bash
# @group: 2
# @name: fuzzy_close_match
# @tags: medium
# @timeout: 90
# @description: Test that fuzzy matching suggests 'run_shell_command' for 'run_commnad'

# @lines: 50

# @count: 6/7

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=2
export TEST_TAGS=("medium")
export TEST_TIMEOUT=90

# Setup - pass the actual test file path, not $0 (which is ./run when sourced)
setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.2_fuzzy_close_match"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Use typo 'run_commnad' - should get suggestion for 'run_shell_command' and succeed
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "run_commnad 'echo hello'")
if expect_contains "hello" "$result" "Fuzzy matching works: 'run_commnad' → 'run_shell_command'" "$TEST_NAME"; then
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
