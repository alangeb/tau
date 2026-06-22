#!/bin/bash
# @group: 9
# @name: tmux_exec_simple
# @tags: fast
# @timeout: 60
# @description: Agent executes command in tmux session using run_background_exec

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=1
export TEST_INDEX=4
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.1.4_tmux_exec_simple"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up ALL existing tmux-agent sessions to start fresh
tmux ls 2>/dev/null | grep "tmux-agent-" | cut -d: -f1 | xargs -r tmux kill-session 2>/dev/null || true
rm -f /tmp/test-exec-output-$$-file.txt 2>/dev/null || true

# Run agent to create session and execute command that writes to file
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create a new tmux session using run_background_new, then execute 'echo hello-from-tmux > /tmp/test-exec-output-$$-file.txt' using run_background_exec")

# Verify file was created by the command (side-effect)
if expect_file_exists "/tmp/test-exec-output-$$-file.txt" "File created by exec command" "$TEST_NAME"; then
    if expect_file_contains "/tmp/test-exec-output-$$-file.txt" "hello-from-tmux" "File contains expected content" "$TEST_NAME"; then
        TEST_RESULT="PASS"
    else
        log_fail "File content incorrect"
        TEST_RESULT="FAIL"
    fi
else
    TEST_RESULT="FAIL"
fi

# Cleanup
rm -f /tmp/test-exec-output-$$-file.txt 2>/dev/null || true

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
