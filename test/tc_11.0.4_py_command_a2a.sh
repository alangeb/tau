#!/bin/bash
# @group: 11
# @name: py_command_a2a
# @tags: fast
# @timeout: 120
# @description: Test .py commands via A2A protocol

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=11
export TEST_SUBGROUP=0
export TEST_INDEX=4
export TEST_TAGS=("fast")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_11.0.4_py_command_a2a"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# ============================================================================
# Start agent with --keep-alive for A2A testing
# ============================================================================

python3 "$DUT_PATH" --keep-alive > "$output_file" 2>&1 &
SHELL_PID=$!

# Wait for agent to start and extract actual PID from log
sleep 3
AGENT_PID=$(grep -oP 'Agent PID: \K[0-9]+' "$output_file" 2>/dev/null || echo "")

if [[ -z "$AGENT_PID" ]]; then
    log_fail "Could not extract agent PID from log"
    kill "$SHELL_PID" 2>/dev/null || true
    TEST_RESULT="FAIL"
    cleanup_test "$BASH_SOURCE"
    exit 1
fi

log_info "Agent PID: $AGENT_PID (shell PID: $SHELL_PID)"

# Wait for A2A socket
A2A_SOCKET="/tmp/taua2a-${AGENT_PID}.sock"
socket_ready=0
for i in $(seq 1 20); do
    if [[ -S "$A2A_SOCKET" ]]; then
        socket_ready=1
        break
    fi
    sleep 0.5
done

if [[ $socket_ready -eq 0 ]]; then
    log_fail "A2A socket not found: $A2A_SOCKET"
    kill "$SHELL_PID" 2>/dev/null || true
    TEST_RESULT="FAIL"
    cleanup_test "$BASH_SOURCE"
    exit 1
fi

log_info "A2A socket found: $A2A_SOCKET"
ALL_PASSED=true

# ============================================================================
# TEST 1: /help via A2A
# ============================================================================

log_info "[COMM] /help"
result=$(python3 "$DUT_PATH" --pid "$AGENT_PID" "/help" 2>&1)
result_clean=$(echo "$result" | sed 's/\x1b\[[0-9;]*m//g')

if ! expect_contains "Built-in Commands" "$result_clean" "A2A /help shows Built-in Commands" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result_clean:0:500}"
    ALL_PASSED=false
fi

if ! expect_contains "External Python Commands" "$result_clean" "A2A /help shows External Python Commands" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result_clean:0:500}"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 2: /commands via A2A
# ============================================================================

log_info "[COMM] /commands"
result2=$(python3 "$DUT_PATH" --pid "$AGENT_PID" "/commands" 2>&1)
result2_clean=$(echo "$result2" | sed 's/\x1b\[[0-9;]*m//g')

if ! expect_contains "delegate" "$result2_clean" "A2A /commands shows delegate" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result2_clean:0:500}"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 3: Unknown command via A2A
# ============================================================================

log_info "[COMM] /nonexistent_xyz"
result3=$(python3 "$DUT_PATH" --pid "$AGENT_PID" "/nonexistent_xyz" 2>&1)
result3_clean=$(echo "$result3" | sed 's/\x1b\[[0-9;]*m//g')

if ! expect_contains "Unknown command" "$result3_clean" "A2A unknown command shows error" "$TEST_NAME"; then
    log_fail "[INPUT] Full result: ${result3_clean:0:500}"
    ALL_PASSED=false
fi

# ============================================================================
# Cleanup
# ============================================================================

kill "$SHELL_PID" 2>/dev/null || true
rm -f "$A2A_SOCKET"

if [[ "$ALL_PASSED" == "true" ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
