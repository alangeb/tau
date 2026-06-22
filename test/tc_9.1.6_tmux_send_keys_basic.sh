#!/bin/bash
# @group: 9
# @name: tmux_send_keys_basic
# @tags: fast
# @timeout: 60
# @description: Agent sends keys to tmux session using run_background_send_keys

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=1
export TEST_INDEX=6
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.1.6_tmux_send_keys_basic"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing sessions with this pattern
tmux kill-session -t test-keys-$$ 2>/dev/null || true

# Run agent to send keys and capture output
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create a tmux session using run_background_new, then send keys 'echo sent-by-keys' using run_background_send_keys, then press enter and capture the output using run_background_capture")

# Verify the command was executed via capture (side-effect in captured pane)
if echo "$result" | grep -qi "sent-by-keys"; then
    log_pass "Captured pane shows command result from send-keys"
    TEST_RESULT="PASS"
else
    log_fail "Could not verify send-keys produced expected output"
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
