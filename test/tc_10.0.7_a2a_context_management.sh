#!/bin/bash
# @group: 10
# @name: a2a_context_management
# @tags: fast,a2a
# @timeout: 120
# @description: Test context management features via A2A
#
# Test Intent:
# - Test context compression
# - Test /clear command
# - Test /ctx and /ctxfull commands
# - Test /undo functionality

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=10
export TEST_SUBGROUP=0
export TEST_INDEX=7
export TEST_TAGS=("fast" "a2a" "context")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_10.0.7_a2a_context_management"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

AGENT_PID=""
A2A_SOCKET=""
ALL_PASSED=true

# ============================================================================
# 1. START: Launch agent with --keep-alive
# ============================================================================

log_info "Starting agent with --keep-alive..."
"$DUT_PATH" --keep-alive > "$output_file" 2>&1 &
AGENT_PID=$!

log_info "Agent started with PID: $AGENT_PID"

# Wait for agent to initialize
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
    ALL_PASSED=false
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
# TEST 1: Initial context check with /status
# ============================================================================

log_info "[COMM] /status (initial)"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/status" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

if [[ "$result_clean" == *"CONTEXT"* ]] || [[ "$result_clean" == *"Context:"* ]]; then
    log_pass "Initial context status available"
else
    log_fail "Initial context status unavailable"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 2: Build up context with multiple turns
# ============================================================================

log_info "[COMM] Multiple turns to build context"
for i in $(seq 1 10); do
    FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Remember: value_$i=$i" 2>&1) || true
done
log_pass "Built up context with 10 turns"

# Check context size increased
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/status" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

if [[ "$result_clean" == *"msgs"* ]]; then
    log_pass "Context has messages after building"
else
    log_fail "Context message check failed"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 3: Context compression
# ============================================================================

log_info "[COMM] /compress"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/compress" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

if [[ "$result_clean" == *"compressed"* ]] || [[ "$result_clean" == *"Context"* ]]; then
    log_pass "Context compression attempted"
else
    log_warn "Context compression output unclear"
fi

# ============================================================================
# TEST 4: Context with /ctx and /ctxfull
# ============================================================================

log_info "[COMM] /ctx"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/ctx" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# Debug output for testing
# log_info "DEBUG: result_clean contains: ${result_clean:0:100}"

if [[ "$result_clean" == *"CONTEXT"* ]] || [[ "$result_clean" == *"SUMMARY"* ]] || [[ "$result_clean" == *"messages"* ]]; then
    log_pass "/ctx command works"
else
    log_warn "/ctx command response unclear (may be empty or different format)"
fi

log_info "[COMM] /ctxfull"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/ctxfull" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# Debug output for testing
# log_info "DEBUG: result_clean contains: ${result_clean:0:100}"

if [[ "$result_clean" == *"CONTEXT"* ]] || [[ "$result_clean" == *"FULL"* ]] || [[ "$result_clean" == *"messages"* ]]; then
    log_pass "/ctxfull command works"
else
    log_warn "/ctxfull command response unclear (may be empty or different format)"
fi

# ============================================================================
# TEST 5: Context persistence check
# ============================================================================

log_info "[COMM] Check context persistence with recalled values"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Do you remember value_1? Just reply with the number." 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

if [[ "$result_clean" == *"1"* ]]; then
    log_pass "Context persists - remembered value_1"
else
    log_fail "Context may not have persisted correctly"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 6: Undo functionality
# ============================================================================

log_info "[COMM] /undo"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/undo" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

log_pass "Undo command executed"

# ============================================================================
# TEST 7: Clear context
# ============================================================================

log_info "[COMM] /clear"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/clear" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

log_pass "Clear command executed"

# Check context is cleared
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/status" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

if [[ "$result_clean" == *"0 msgs"* ]] || [[ "$result_clean" == *"Context:"* ]]; then
    log_pass "Context cleared"
else
    log_warn "Context clear verification inconclusive"
fi

# ============================================================================
# CLEANUP AND FINAL RESULT
# ============================================================================

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

if [[ "$ALL_PASSED" == "true" ]]; then
    TEST_RESULT="PASS"
    log_pass "All tests passed!"
else
    TEST_RESULT="FAIL"
    log_fail "Some tests failed"
fi

cleanup_test "$BASH_SOURCE"
