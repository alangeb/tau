#!/bin/bash
# @group: 1
# @name: ctxfull_command
# @tags: fast
# @timeout: 60
# @description: Test /ctxfull command shows full context

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=1
export TEST_INDEX=7
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_1.1.7_ctxfull_command"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "/ctx")

if expect_contains "CONTEXT SUMMARY" "$result" "Should show context summary header" "$TEST_NAME"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
