#!/bin/bash
# @group: 9
# @name: tmux_cross_session_communication
# @tags: fast
# @timeout: 90
# @description: Two tmux sessions share a file - read/write between sessions

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=5
export TEST_TAGS=("fast")
export TEST_TIMEOUT=90

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.5_tmux_cross_session_communication"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up ALL existing tmux-agent sessions to start fresh
tmux ls 2>/dev/null | grep "tmux-agent-" | cut -d: -f1 | xargs -r tmux kill-session 2>/dev/null || true
rm -f /tmp/cross-session-$$-file.txt 2>/dev/null || true

# Session A: Write to shared file
result_a=$(run_tool_capture "$output_file.a" "$TEST_TIMEOUT" "create a new tmux session, then execute 'echo message-from-session-a > /tmp/cross-session-$$-file.txt' in that session")

# Verify file was created
FILE_CREATED=false
if expect_file_exists "/tmp/cross-session-$$-file.txt" "Shared file created by Session A" "$TEST_NAME"; then
    FILE_CREATED=true
fi

# Session B: Read from shared file (using a new session)
result_b=$(run_tool_capture "$output_file.b" "$TEST_TIMEOUT" "create a new tmux session, then execute 'cat /tmp/cross-session-$$-file.txt' in that session and show me the output")

# Verify Session B could read what Session A wrote
CROSS_READ_SUCCESS=false
if echo "$result_b" | grep -qi "message-from-session-a"; then
    log_pass "Session B successfully read file written by Session A"
    CROSS_READ_SUCCESS=true
else
    log_fail "Session B could not read content from Session A's file"
fi

# Cleanup
rm -f /tmp/cross-session-$$-file.txt 2>/dev/null || true

if $FILE_CREATED && $CROSS_READ_SUCCESS; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
