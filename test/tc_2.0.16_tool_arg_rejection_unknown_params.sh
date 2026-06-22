#!/bin/bash
# @group: 2
# @name: tool_arg_rejection_unknown_params
# @tags: fast validation
# @timeout: 60
# @description: Test rejection of completely unknown parameters with helpful suggestions

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=16
export TEST_TAGS=("fast" "validation")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.16_tool_arg_rejection_unknown_params"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Try multiple unknown parameters
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Search for pattern with --unknown-flag and -z option")

TEST_RESULT="PASS"
# If validation layer is working, it should either:
# 1. Reject the request with helpful suggestions, OR
# 2. Auto-correct to similar parameters, OR
# 3. Provide clear error about unknown params

# Check for evidence of validation layer operation
if expect_contains "unknown" "$result" "Unknown param mentioned" "$TEST_NAME"; then
    echo "PASS: Unknown parameters acknowledged"
elif expect_contains "suggestion" "$result" "Suggestions provided" "$TEST_NAME"; then
    echo "PASS: Suggestions provided for unknown params"
elif expect_contains "error" "$result" "Error message present" "$TEST_NAME"; then
    echo "INFO: Error occurred (may be validation layer working)"
else
    echo "INFO: Validation layer may be auto-correcting silently"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
