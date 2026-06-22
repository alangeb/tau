#!/bin/bash
# @group: 9
# @name: tmux_ls
# @tags: fast
# @timeout: 60
# @description: Agent lists tmux sessions using run_background_ls

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=1
export TEST_INDEX=2
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.1.2_tmux_ls"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up ALL existing tmux-agent sessions to start fresh
tmux ls 2>/dev/null | grep "tmux-agent-" | cut -d: -f1 | xargs -r tmux kill-session 2>/dev/null || true

# Count sessions before
COUNT_BEFORE=$(tmux ls 2>/dev/null | grep "tmux-agent-" | wc -l || true)

# Run agent to create 2 sessions and list them
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create two new sessions using run_background_new, then list all sessions using run_background_ls")

# Count sessions after
COUNT_AFTER=$(tmux ls 2>/dev/null | grep "tmux-agent-" | wc -l || true)

# Verify 2 new sessions were created via tmux ls (side-effect)
SESSIONS_CREATED=$((COUNT_AFTER - COUNT_BEFORE))
if [[ "$SESSIONS_CREATED" -eq 2 ]]; then
    log_pass "Two new sessions created (before=$COUNT_BEFORE, after=$COUNT_AFTER)"
    TEST_RESULT="PASS"
else
    log_fail "Expected 2 new sessions, found $SESSIONS_CREATED (before=$COUNT_BEFORE, after=$COUNT_AFTER)"
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
