#!/bin/bash
# @group: 10
# @name: a2a_sanity
# @tags: fast,a2a,sanity
# @timeout: 60
# @description: Verify A2A communication works at basic level (single arithmetic query)
#
# Test Intent:
# - Quick sanity check that A2A (agent-to-agent) protocol is functioning
# - Verifies: socket creation, query transmission, response reception
# - Single arithmetic test (deterministic result: 112233*2 = 224466)
# - Performance: ~5-10 seconds total (one agent startup)
#
# Test Flow:
# 1. START: Launch agent with --keep-alive (persistent session)
# 2. WAIT: Poll for A2A socket (/tmp/taua2a-{PID}.sock) up to 5 seconds
# 3. QUERY: Send A2A query "112233*2" via tool --pid {pid}
# 4. VALIDATE: Response contains "224466"
# 5. CLEANUP: Kill agent, remove socket
#
# Comparison to tc_10.0.2:
# - tc_10.0.1: Single query, simpler logic, faster feedback
# - tc_10.0.2: Multiple queries batched, aggregates pass/fail

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=10
export TEST_SUBGROUP=0
export TEST_INDEX=1
export TEST_TAGS=("fast" "a2a" "sanity")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_10.0.1_a2a_sanity"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

AGENT_PID=""
A2A_SOCKET=""

# ============================================================================
# 1. START: Launch agent with --keep-alive for persistent session
# ============================================================================

log_info "Starting agent with --keep-alive..."
"$DUT_PATH" --keep-alive > "$output_file" 2>&1 &
AGENT_PID=$!

log_info "Agent started with PID: $AGENT_PID"

# Wait for agent to initialize and create A2A socket
sleep 3

# ============================================================================
# 2. WAIT: Poll for A2A socket
# ============================================================================

A2A_SOCKET="/tmp/taua2a-${AGENT_PID}.sock"
socket_ready=0

for i in $(seq 1 10); do
    if [[ -S "$A2A_SOCKET" ]]; then
        log_pass "A2A socket ready after ${i} attempts: $A2A_SOCKET"
        socket_ready=1
        break
    fi
    sleep 0.5
done

if [[ $socket_ready -eq 0 ]]; then
    log_fail "A2A socket not created after 5 seconds"
    TEST_RESULT="FAIL"
    # Cleanup before exit
    if [[ -n "$AGENT_PID" ]] && kill -0 "$AGENT_PID" 2>/dev/null; then
        kill "$AGENT_PID" 2>/dev/null || true
        sleep 1
    fi
    end_time=$(date +%s.%N)
    TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")
    cleanup_test "$BASH_SOURCE"
    exit 1
fi

log_info "A2A socket confirmed: $A2A_SOCKET"

# ============================================================================
# 3. QUERY: Send single arithmetic query via A2A
# ============================================================================

log_info "Sending A2A query: 112233*2"
result=$("$DUT_PATH" --pid "$AGENT_PID" "How much is 112233*2? Answer only the plain number." 2>&1)

log_info "Received response: ${result:0:50}..."

# ============================================================================
# 4. VALIDATE: Check response contains correct result
# ============================================================================

if echo "$result" | grep -qi "224466"; then
    log_pass "A2A query returned correct result (224466)"
    TEST_RESULT="PASS"
else
    log_fail "A2A query did not return correct result. Got: $result"
    TEST_RESULT="FAIL"
fi

# ============================================================================
# 5. CLEANUP: Kill agent and remove socket
# ============================================================================

cleanup_a2a_agent "$AGENT_PID"

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"

# Archive failure if needed
if [[ "$TEST_RESULT" == "FAIL" ]]; then
    archive_failure "$TEST_NAME" "$TEST_OUTPUT_DIR" "$output_file" "" ""
fi
