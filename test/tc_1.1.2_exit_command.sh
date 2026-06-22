#!/bin/bash
# @group: 1
# @name: exit_command
# @tags: fast
# @timeout: 60
# @description: Test /exit command stops execution, subsequent commands never run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=1
export TEST_INDEX=2
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_1.1.2_exit_command"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# This testcase is very deliberate. We tell the agent X and Y (and later parse for it - just to be sure we really passed it).
# The actual test happens next prompts, we ask the agent to exit, then ask it to calculate X+Y.
# The agent should never reach the X+Y calculation if exit works - so by testing that X+Y result is not provided we tested the exit command.

# Run agent with /exit followed by commands that should never execute
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Set X to 111111 (just remember)" "Set Y to 222222 (just remember)" "/exit" "X+Y (calculate yourself, just answer plain number as result)" "What is the capitol of france")

# Check output contains /exit acknowledgment
if expect_contains "EXIT SUMMARY" "$result" "Agent should acknowledge /exit" "$TEST_NAME"; then
    # Positive expect: 111111 should appear
    if expect_contains "111111" "$result" "X=111111 should be processed" "$TEST_NAME"; then
        # Positive expect: 222222 should appear
        if expect_contains "222222" "$result" "Y=222222 should be processed" "$TEST_NAME"; then
            # Negative expect: X+Y command should not appear (not processed)
            if expect_not_contains "333333" "$result" "333333 command should never be processed" "$TEST_NAME"; then
                # Negative expect: Paris should not appear (case insensitive)
                if expect_not_contains "paris" "$result" "Capital of france question should never be answered so paris should not appear" "$TEST_NAME"; then
                    TEST_RESULT="PASS"
                else
                    TEST_RESULT="FAIL"
                fi
            else
                TEST_RESULT="FAIL"
            fi
        else
            TEST_RESULT="FAIL"
        fi
    else
        TEST_RESULT="FAIL"
    fi
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
