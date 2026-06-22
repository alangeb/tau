#!/bin/bash
# @group: 9
# @name: tmux_parallel_racy_condition
# @tags: fast
# @timeout: 120
# @description: Two parallel tmux sessions compete to write same file - verify race condition handling

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=11
export TEST_TAGS=("fast")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.11_tmux_parallel_racy_condition"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing tmux-agent sessions
tmux ls 2>/dev/null | grep "tmux-agent-" | cut -d: -f1 | xargs -r tmux kill-session 2>/dev/null || true
rm -f /tmp/race-condition-$$-file.txt 2>/dev/null || true

# Run two agents in parallel, both trying to write to the SAME file
# This tests parallel session behavior and potential race conditions
# Note: run_background tool auto-generates session names as tmux-agent-{uuid}
(
    run_tool_capture "$output_file.a" "$TEST_TIMEOUT" "create a new tmux session using run_background_new, then use run_background_exec to run 'echo line-from-session-a >> /tmp/race-condition-$$-file.txt' in that session" 2>&1 > /dev/null
) &
PID_A=$!

# Small delay to ensure both sessions start nearly simultaneously
sleep 0.1

(
    run_tool_capture "$output_file.b" "$TEST_TIMEOUT" "create a new tmux session using run_background_new, then use run_background_exec to run 'echo line-from-session-b >> /tmp/race-condition-$$-file.txt' in that session" 2>&1 > /dev/null
) &
PID_B=$!

wait $PID_A $PID_B

# Verify file exists (side-effect)
FILE_EXISTS=false
if expect_file_exists "/tmp/race-condition-$$-file.txt" "Race condition file created" "$TEST_NAME"; then
    FILE_EXISTS=true
fi

# Verify file contains content from at least one session
# (both lines may not appear due to race, but at least one should)
HAS_CONTENT_A=false
HAS_CONTENT_B=false
HAS_AT_LEAST_ONE=false

if expect_file_contains "/tmp/race-condition-$$-file.txt" "line-from-session-a" "File contains session A content" "$TEST_NAME"; then
    HAS_CONTENT_A=true
    HAS_AT_LEAST_ONE=true
fi

if expect_file_contains "/tmp/race-condition-$$-file.txt" "line-from-session-b" "File contains session B content" "$TEST_NAME"; then
    HAS_CONTENT_B=true
    HAS_AT_LEAST_ONE=true
fi

# Show file contents for debugging
if $FILE_EXISTS; then
    log_info "File contents:"
    cat /tmp/race-condition-$$-file.txt
fi

# Cleanup
rm -f /tmp/race-condition-$$-file.txt 2>/dev/null || true

# Test passes if file exists and has content from at least one session
if $FILE_EXISTS && $HAS_AT_LEAST_ONE; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
