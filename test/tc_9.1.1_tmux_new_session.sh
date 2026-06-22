#!/bin/bash
# @group: 9
# @name: tmux_new_session
# @tags: fast
# @timeout: 60
# @description: Agent creates new tmux session using run_background_new

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=1
export TEST_INDEX=1
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.1.1_tmux_new_session"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up ALL existing tmux-agent sessions to start fresh
tmux ls 2>/dev/null | grep "tmux-agent-" | cut -d: -f1 | xargs -r tmux kill-session 2>/dev/null || true

# Count sessions before
COUNT_BEFORE=$(tmux ls 2>/dev/null | grep "tmux-agent-" | wc -l || true)

# Run agent to create new session
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create a new session using run_background_new")

# Count sessions after
COUNT_AFTER=$(tmux ls 2>/dev/null | grep "tmux-agent-" | wc -l || true)

# Verify via tmux ls (side-effect) - session count increased
if [[ "$COUNT_AFTER" -gt "$COUNT_BEFORE" ]]; then
    log_pass "New session created (before=$COUNT_BEFORE, after=$COUNT_AFTER)"
    TEST_RESULT="PASS"
else
    log_fail "No new session created (before=$COUNT_BEFORE, after=$COUNT_AFTER)"
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
