#!/bin/bash
# @group: 1
# @name: status_command
# @tags: fast
# @timeout: 60
# @description: Test /status command shows agent status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=1
export TEST_INDEX=10
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_1.1.10_status_command"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "/status")

# Extract and validate numeric values using helper function (avoids code duplication)
# Strip ANSI color codes first
result_stripped=$(echo "$result" | sed 's/\x1b\[[0-9;]*m//g')
msgs=$(echo "$result_stripped" | grep -oE "Context: [0-9]+ msgs" | grep -oE '[0-9]+' | head -1)
# Session total line format: "Session total: 0 in + 0 out + 0 cached = 0 total"
tokens=$(echo "$result_stripped" | grep -oE "Session total: [0-9,]+ in" | grep -oE '[0-9,]+' | head -1 | tr -d ',')

if [[ -n "$msgs" && -n "$tokens" ]]; then
    if [[ "$msgs" -gt 0 && "$tokens" -ge 0 ]]; then
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
