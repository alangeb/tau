#!/bin/bash
# @group: 1
# @name: help_command
# @tags: fast
# @timeout: 60
# @description: Test /help command returns expected output including /toolsjson

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=1
export TEST_INDEX=1
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

# Setup - pass the actual test file path, not $0 (which is ./run when sourced)
setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_1.1.1_help_command"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# This test has been reviewed and is fine. We issue /help, we expect the help text to be part of the reply, /toolsjson is one of the commands we expect to see in help text

# Run agent with /help input
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "/help")
if expect_contains "/help" "$result" "Output should contain /help" "$TEST_NAME"; then
    if expect_contains "/toolsjson" "$result" "Output should contain /toolsjson" "$TEST_NAME"; then
        TEST_RESULT="PASS"
    else
        TEST_RESULT="FAIL"
    fi
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

# Cleanup
cleanup_test "$BASH_SOURCE"
