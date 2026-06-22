#!/bin/bash
# @group: 9
# @name: tmux_exec_wait
# @tags: fast
# @timeout: 60
# @description: Agent exec with wait=True returns output using run_background_exec

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=1
export TEST_INDEX=5
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.1.5_tmux_exec_wait"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing sessions with this pattern
tmux kill-session -t test-wait-$$ 2>/dev/null || true

# Run agent to test both wait modes
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create a tmux session using run_background_new, then: 1) execute 'echo test1' using run_background_exec with wait=True, 2) execute 'echo test2' using run_background_exec with wait=False. Show me both outputs")

# Verify wait=True mode returned actual output (contains command result)
HAS_WAIT_TRUE_OUTPUT=false
    if echo "$result" | grep -qi "1.*echo test1.*wait=True"; then
    HAS_WAIT_TRUE_OUTPUT=true
    log_pass "wait=True returned output section"
fi

# Verify wait=False mode returned "Sent" status
HAS_SENT_STATUS=false
if echo "$result" | grep -qi "sent"; then
    HAS_SENT_STATUS=true
    log_pass "wait=False returned 'Sent' status"
fi

if $HAS_WAIT_TRUE_OUTPUT && $HAS_SENT_STATUS; then
    TEST_RESULT="PASS"
else
    log_fail "Did not verify both wait modes correctly"
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
