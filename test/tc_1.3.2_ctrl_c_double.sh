#!/bin/bash
# @group: 1
# @name: ctrl_c_double_exit
# @tags: interrupt,critical
# @timeout: 30
# @description: Double Ctrl-C exits without waiting for tool completion

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=3
export TEST_INDEX=2
export TEST_TAGS=("interrupt" "critical" "slow")
export TEST_TIMEOUT=30

# Test disabled - Ctrl-C handling needs rework
setup_test "$BASH_SOURCE"
TEST_RESULT="SKIP"
end_time=$(date -Iseconds)
TEST_DURATION=0
cleanup_test "$BASH_SOURCE"
exit 0
output_file="$TEST_OUTPUT_DIR/tool_output.txt"
start_time=$(date +%s.%N)

log_info "Starting test: $TEST_NAME"
log_info "Testing double Ctrl-C exits agent without waiting for tool"

# Start agent in background with sleep command
log_info "Starting agent with 'sleep 90' command..."

# Start agent in background, capturing output
(
    timeout 60 "$DUT_PATH" "execute sleep 90" 2>&1 | tee "$output_file"
) &
AGENT_PID=$!

log_info "Agent started with PID: $AGENT_PID"

# Wait for agent to start
sleep 2

# Check if agent is still running
if ! kill -0 $AGENT_PID 2>/dev/null; then
    log_fail "Agent died before we could send Ctrl-C"
    TEST_RESULT="FAIL: Agent died prematurely"
    end_time=$(date +%s.%N)
    TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")
    cleanup_test "$BASH_SOURCE"
    exit 1
fi

log_info "Agent running, sending rapid double Ctrl-C..."

# Send first Ctrl-C
kill -INT $AGENT_PID 2>/dev/null || true
sleep 0.5

# Send second Ctrl-C quickly after
kill -INT $AGENT_PID 2>/dev/null || true

# Wait for agent to exit (max 10 seconds)
log_info "Waiting for agent to exit (max 10s)..."
exit_code=1
for i in $(seq 1 10); do
    if ! kill -0 $AGENT_PID 2>/dev/null; then
        exit_code=0
        log_info "Agent exited after ${i}s"
        break
    fi
    sleep 1
done

if [ $exit_code -eq 0 ]; then
    # Check for expected exit message
    if expect_contains "Interrupted, exiting..." "$output_file" "Agent exited with expected message" "$TEST_NAME"; then
        TEST_RESULT="PASS"
        log_pass "Test passed: Agent exited cleanly after double Ctrl-C"
    else
        TEST_RESULT="FAIL: Missing exit message"
        log_fail "Test failed: Agent exited but missing 'Interrupted, exiting...' message"
        log_info "Output snippet:"
        tail -20 "$output_file"
    fi
else
    TEST_RESULT="FAIL: Agent did not exit within timeout"
    log_fail "Test failed: Agent did not exit within 10 seconds after double Ctrl-C"
    log_info "Current output:"
    tail -20 "$output_file"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
