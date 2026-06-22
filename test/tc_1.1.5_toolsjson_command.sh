#!/bin/bash
# @group: 1
# @name: toolsjson_command
# @tags: fast
# @timeout: 60
# @description: Test /toolsjson command outputs tools as JSON

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=1
export TEST_INDEX=5
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_1.1.5_toolsjson_command"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "/tools")

if expect_contains "bash" "$result" "Should list available tools" "$TEST_NAME"; then
    if expect_contains "file_write" "$result" "Should include file_write tool" "$TEST_NAME"; then
        TEST_RESULT="PASS"
    else
        TEST_RESULT="FAIL"
    fi
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
