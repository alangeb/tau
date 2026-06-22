#!/bin/bash
# @group: 9
# @name: tmux_parallel_sessions_write
# @tags: fast
# @timeout: 120
# @description: Two parallel tmux sessions using run_background_new

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=3
export TEST_TAGS=("fast")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.3_tmux_parallel_sessions_write"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing tmux-agent sessions
tmux ls 2>/dev/null | grep "tmux-agent-" | cut -d: -f1 | xargs -r tmux kill-session 2>/dev/null || true
rm -f /tmp/parallel-a-$$-file.txt /tmp/parallel-b-$$-file.txt 2>/dev/null || true

# Run two agents in parallel, each creating a session and writing a file
(
    run_tool_capture "$output_file.a" "$TEST_TIMEOUT" "create a new tmux session using run_background_new, list sessions using run_background_ls to get the name, then execute 'echo content-a > /tmp/parallel-a-$$-file.txt' using run_background_exec" 2>&1 > /dev/null
) &
PID_A=$!

(
    run_tool_capture "$output_file.b" "$TEST_TIMEOUT" "create a new tmux session using run_background_new, list sessions using run_background_ls to get the name, then execute 'echo content-b > /tmp/parallel-b-$$-file.txt' using run_background_exec" 2>&1 > /dev/null
) &
PID_B=$!

wait $PID_A $PID_B

# Verify both files exist (side-effect)
FILE_A_EXISTS=false
FILE_B_EXISTS=false

if expect_file_exists "/tmp/parallel-a-$$-file.txt" "File A created by parallel session" "$TEST_NAME"; then
    FILE_A_EXISTS=true
fi

if expect_file_exists "/tmp/parallel-b-$$-file.txt" "File B created by parallel session" "$TEST_NAME"; then
    FILE_B_EXISTS=true
fi

# Verify file contents
CONTENT_A_CORRECT=false
CONTENT_B_CORRECT=false

if expect_file_contains "/tmp/parallel-a-$$-file.txt" "content-a" "File A has correct content" "$TEST_NAME"; then
    CONTENT_A_CORRECT=true
fi

if expect_file_contains "/tmp/parallel-b-$$-file.txt" "content-b" "File B has correct content" "$TEST_NAME"; then
    CONTENT_B_CORRECT=true
fi

# Cleanup
rm -f /tmp/parallel-a-$$-file.txt /tmp/parallel-b-$$-file.txt 2>/dev/null || true

if $FILE_A_EXISTS && $FILE_B_EXISTS && $CONTENT_A_CORRECT && $CONTENT_B_CORRECT; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
