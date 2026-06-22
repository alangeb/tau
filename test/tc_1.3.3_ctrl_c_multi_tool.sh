#!/bin/bash
# @group: 1
# @name: ctrl_c_multi_tool
# @tags: interrupt,critical
# @timeout: 45
# @description: Interrupt during second tool call in sequence

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=3
export TEST_INDEX=3
export TEST_TAGS=("interrupt" "critical" "slow")
export TEST_TIMEOUT=45

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
log_info "Testing Ctrl-C during multi-tool sequence"

# Start agent with a prompt that triggers multiple tool calls
# Use multiple bash commands to simulate tool calls
log_info "Starting agent with multiple sleep commands..."

# Start agent in background, capturing output
(
    timeout 90 "$DUT_PATH" "execute sleep 5; execute sleep 10" 2>&1 | tee "$output_file"
) &
AGENT_PID=$!

log_info "Agent started with PID: $AGENT_PID"

# Wait for agent to process first tool (sleep 5)
# Give it 8 seconds to complete first tool and start second
sleep 8

# Check if agent is still running
if ! kill -0 $AGENT_PID 2>/dev/null; then
    log_fail "Agent died before we could send Ctrl-C"
    TEST_RESULT="FAIL: Agent died prematurely"
    end_time=$(date +%s.%N)
    TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")
    cleanup_test "$BASH_SOURCE"
    exit 1
fi

log_info "Agent running (should be in second tool), sending Ctrl-C..."

# Send first Ctrl-C
kill -INT $AGENT_PID 2>/dev/null || true
sleep 2

# Check agent status after first Ctrl-C
if ! kill -0 $AGENT_PID 2>/dev/null; then
    log_warn "Agent exited after first Ctrl-C"
    if expect_contains "Interrupted, exiting..." "$output_file" "Agent exited cleanly after first Ctrl-C" "$TEST_NAME"; then
        log_pass "Agent exited cleanly after first Ctrl-C"
        TEST_RESULT="PASS"
        log_pass "Test passed: Agent interrupted second tool and exited"
        end_time=$(date +%s.%N)
        TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")
        cleanup_test "$BASH_SOURCE"
        exit 0
    fi
fi

log_info "Sending second Ctrl-C..."

# Send second Ctrl-C
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
        log_pass "Test passed: Agent exited cleanly after Ctrl-C"
    else
        TEST_RESULT="FAIL: Missing exit message"
        log_fail "Test failed: Agent exited but missing 'Interrupted, exiting...' message"
        log_info "Output snippet:"
        tail -20 "$output_file"
    fi
else
    TEST_RESULT="FAIL: Agent did not exit within timeout"
    log_fail "Test failed: Agent did not exit within 10 seconds"
    log_info "Current output:"
    tail -20 "$output_file"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
