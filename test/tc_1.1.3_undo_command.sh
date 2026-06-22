#!/bin/bash
# @group: 1
# @name: undo_command
# @tags: fast
# @timeout: 60
# @description: Test /undo command acknowledgment and message removal

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=1
export TEST_INDEX=3
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_1.1.3_undo_command"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Run agent with stdin input (interactive mode) - /undo removes conversation messages
# Use /exec to set variables and test undo behavior

# This test is again very deliberate, we test the /undo command. In below sequence the correct result thus needs to be 333333, and not 666666, IF /undo worked correctly

result=$(printf "%s\n" "Let be X=111111" "Let be Y=222222" "Now be Y=555555" "/undo" "Calculate X+Y and show me the result" | timeout "$TEST_TIMEOUT" "$DUT_PATH" 2>&1 | tee "$output_file")

pass=1

# Check /undo produces acknowledgment message
expect_contains "Undid" "$result" "Undo should acknowledge message removal" "$TEST_NAME" || pass=0

# After /undo, Y should be restored to 222222 (undo should remove Y=555555)
# X+Y should equal 333333 (111111 + 222222)
expect_contains "333333" "$result" "X+Y should be 333333 after undo" "$TEST_NAME" || pass=0

# Verify 666666 is NOT in output (would indicate Y=555555 is still active)
expect_not_contains "666666" "$result" "X+Y should NOT be 666666" "$TEST_NAME" || pass=0

TEST_RESULT="PASS"
[[ $pass -ne 1 ]] && TEST_RESULT="FAIL"

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
