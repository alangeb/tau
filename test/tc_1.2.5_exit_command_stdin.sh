#!/bin/bash
# @group: 1
# @name: exit_command_stdin
# @tags: fast
# @timeout: 60
# @description: Test /exit command via stdin input mode (INTERACTIVE MODE)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=2
export TEST_INDEX=5
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_1.2.5_exit_command_stdin"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Run agent with stdin input (interactive mode) - /exit followed by commands that should never run
result=$(echo -e "Set X to 111111\nSet Y to 222222\n/exit\nX+Y\nWhat is the capital of france" | timeout "$TEST_TIMEOUT" "$DUT_PATH" 2>&1 | tee "$output_file")

pass=1
# Check output contains /exit acknowledgment
echo "$result" | grep -qi "EXIT SUMMARY" || pass=0
# X and Y should be processed
echo "$result" | grep -q "111111" || pass=0
echo "$result" | grep -q "222222" || pass=0
# X+Y should NOT appear (not processed after /exit)
echo "$result" | grep -q "X+Y" && pass=0
# Paris should NOT appear (capital of france question never answered)
echo "$result" | grep -qi "paris" && pass=0

TEST_RESULT="PASS"
[[ $pass -ne 1 ]] && TEST_RESULT="FAIL"

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
