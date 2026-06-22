#!/bin/bash
# @group: 9
# @name: tmux_kill_session
# @tags: fast
# @timeout: 60
# @description: Agent kills tmux session using run_background_kill

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=1
export TEST_INDEX=3
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.1.3_tmux_kill_session"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing sessions with this pattern
tmux kill-session -t tmux-agent-$$ 2>/dev/null || true

# First create the session
tmux new-session -d -s tmux-agent-$$ bash

# Verify it exists before killing
if ! tmux ls | grep -q "tmux-agent-$$"; then
    log_fail "Failed to create test session"
    TEST_RESULT="FAIL"
    exit 1
fi

# Run agent to kill the session
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "kill the session named tmux-agent-$$ using run_background_kill")

# Verify session is gone via tmux ls (side-effect)
if tmux ls 2>/dev/null | grep -q "tmux-agent-$$"; then
    log_fail "Session still exists after kill command"
    TEST_RESULT="FAIL"
else
    log_pass "Session successfully deleted (not in tmux ls output)"
    TEST_RESULT="PASS"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
