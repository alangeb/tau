#!/bin/bash
# @group: 9
# @name: tmux_timing_delay
# @tags: fast
# @timeout: 60
# @description: Agent uses sleep in tmux session - verify timing behavior

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=9
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.9_tmux_timing_delay"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing sessions with this pattern
tmux kill-session -t test-timing-$$ 2>/dev/null || true
rm -f /tmp/timing-test-$$-file.txt 2>/dev/null || true

# Run agent to execute sleep and verify completion
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create a tmux session named test-timing-$$, then execute 'sleep 0.1 && echo completed > /tmp/timing-test-$$-file.txt' with wait=True")

# Verify file was created (command completed after sleep)
if expect_file_exists "/tmp/timing-test-$$-file.txt" "File created after sleep completed" "$TEST_NAME"; then
    if expect_file_contains "/tmp/timing-test-$$-file.txt" "completed" "File contains completion marker" "$TEST_NAME"; then
        TIMING_SUCCESS=true
    else
        log_fail "File does not contain expected content"
        TIMING_SUCCESS=false
    fi
else
    log_fail "File not created - sleep command may not have completed"
    TIMING_SUCCESS=false
fi

# Cleanup
rm -f /tmp/timing-test-$$-file.txt 2>/dev/null || true

if $TIMING_SUCCESS; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
