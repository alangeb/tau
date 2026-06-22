#!/bin/bash
# @group: 9
# @name: tmux_session_cleanup
# @tags: fast
# @timeout: 90
# @description: Verify agent can manage tmux sessions via run_background tools

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=6
export TEST_TAGS=("fast")
export TEST_TIMEOUT=90

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.6_tmux_session_cleanup"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing agent sessions from previous runs
for session in $(tmux ls 2>/dev/null | grep "tmux-agent-" | cut -d: -f1); do
    tmux kill-session -t "$session" 2>/dev/null || true
done

# Wait for cleanup to complete
sleep 1

# Count sessions before test
SESSIONS_BEFORE=$(tmux ls 2>/dev/null | grep -c "tmux-agent-" || echo "0")
SESSIONS_BEFORE=$(echo "$SESSIONS_BEFORE" | tr -d ' \n')
SESSIONS_BEFORE=${SESSIONS_BEFORE:-0}

# Run agent to create 3 sessions, then kill one using run_background tools
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Create three tmux sessions using run_background_new, then kill one of them using run_background_kill, and finally list the remaining sessions using run_background_ls.")

# Count sessions after test
SESSIONS_AFTER=$(tmux ls 2>/dev/null | grep -c "tmux-agent-" || echo "0")
SESSIONS_AFTER=$(echo "$SESSIONS_AFTER" | tr -d ' \n')
SESSIONS_AFTER=${SESSIONS_AFTER:-0}

pass=1

# Verify that run_background tools were used (not run_shell_command)
if grep -q "run_background_new" "$output_file"; then
    log_pass "Agent used run_background_new tool"
else
    log_fail "Agent did not use run_background_new tool"
    pass=0
fi

if grep -q "run_background_kill" "$output_file"; then
    log_pass "Agent used run_background_kill tool"
else
    log_fail "Agent did not use run_background_kill tool"
    pass=0
fi

if grep -q "run_background_ls" "$output_file"; then
    log_pass "Agent used run_background_ls tool"
else
    log_fail "Agent did not use run_background_ls tool"
    pass=0
fi

# Verify sessions were created and one was killed
# We expect: SESSIONS_AFTER = SESSIONS_BEFORE + 3 - 1 = SESSIONS_BEFORE + 2
EXPECTED_SESSIONS=$((SESSIONS_BEFORE + 2))
if [[ "$SESSIONS_AFTER" -eq "$EXPECTED_SESSIONS" ]]; then
    log_pass "Correct number of sessions after test (before=$SESSIONS_BEFORE, after=$SESSIONS_AFTER, expected=$EXPECTED_SESSIONS)"
else
    log_fail "Session count mismatch (before=$SESSIONS_BEFORE, after=$SESSIONS_AFTER, expected=$EXPECTED_SESSIONS)"
    pass=0
fi

# Verify agent output mentions creating sessions and killing one
if echo "$result" | grep -qi "created.*session\|create.*session"; then
    log_pass "Agent output mentions creating sessions"
else
    log_fail "Agent output doesn't mention creating sessions"
    pass=0
fi

if echo "$result" | grep -qi "kill\|removed\|deleted"; then
    log_pass "Agent output mentions killing a session"
else
    log_fail "Agent output doesn't mention killing a session"
    pass=0
fi

if echo "$result" | grep -qi "remaining\|list\|two"; then
    log_pass "Agent output mentions remaining sessions"
else
    log_fail "Agent output doesn't mention remaining sessions"
    pass=0
fi

if [[ $pass -eq 1 ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
