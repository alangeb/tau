#!/bin/bash
# @group: 10
# @name: a2a_commands
# @tags: fast,a2a
# @timeout: 120
# @description: Test custom command creation, execution, and removal via A2A
#
# Test Intent:
# - Create custom command via A2A
# - Execute custom command and verify functionality
# - List commands via /commands
# - Remove custom command
# - Verify command is gone from /commands

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=10
export TEST_SUBGROUP=0
export TEST_INDEX=9
export TEST_TAGS=("fast" "a2a" "commands")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_10.0.9_a2a_commands"
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
# TEST 1: Verify initial /commands output
# ============================================================================

log_info "[COMM] /commands (initial - should have built-in commands)"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/commands" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# Check for built-in commands
if [[ "$result_clean" == *"/recap"* ]] || [[ "$result_clean" == *"/help"* ]]; then
    log_pass "Initial /commands shows built-in commands"
else
    log_fail "Initial /commands unexpected"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 2: Create a custom command
# ============================================================================

log_info "[COMM] Create custom command 'testcommand' via file write"
# Note: We write directly to the commands directory via shell since we're outside the agent's context
# Use absolute path from original directory
COMMANDS_DIR="$HOME/tau/src/commands"
cat > "$COMMANDS_DIR/testcommand.md" << 'EOF'
---
name: testcommand
signature: testcommand <value>
description: Test command that echoes the value
---

I will remember and echo back: $1
EOF

if [[ -f "$COMMANDS_DIR/testcommand.md" ]]; then
    log_pass "Custom command file created"
else
    log_fail "Custom command file not created"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 3: Verify command appears in /commands
# ============================================================================

log_info "[COMM] /commands (after creating custom command)"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/commands" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

if [[ "$result_clean" == *"/testcommand"* ]]; then
    log_pass "Custom command appears in /commands"
else
    log_fail "Custom command not found in /commands"
    log_fail "Result: ${result_clean:0:200}"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 4: Execute the custom command
# ============================================================================

log_info "[COMM] /testcommand HelloWorld"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/testcommand HelloWorld" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# The command content is sent as a user message to the agent
# which will then respond. We check that the agent responded.
if [[ "$result_clean" == *"HelloWorld"* ]] || [[ "$result_clean" == *"Hello"* ]] || [[ "$result_clean" == *"will remember"* ]]; then
    log_pass "Custom command executed (agent received and processed)"
else
    log_warn "Custom command result unclear: ${result_clean:0:150}"
fi

# ============================================================================
# TEST 5: Check /help shows the command
# ============================================================================

log_info "[COMM] /help (should include testcommand)"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/help" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

if [[ "$result_clean" == *"/testcommand"* ]]; then
    log_pass "Custom command appears in /help"
else
    log_warn "Custom command not found in /help (may be ok)"
fi

# ============================================================================
# TEST 6: Remove the custom command
# ============================================================================

log_info "[COMM] Remove custom command file"
rm -f "$COMMANDS_DIR/testcommand.md"

if [[ ! -f "$COMMANDS_DIR/testcommand.md" ]]; then
    log_pass "Custom command file removed"
else
    log_fail "Custom command file not removed"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 7: Verify command is gone from /commands
# ============================================================================

log_info "[COMM] /commands (after removal)"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/commands" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

if [[ "$result_clean" != *"/testcommand"* ]]; then
    log_pass "Custom command removed from /commands"
else
    log_fail "Custom command still appears in /commands"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 8: Execute removed command (should fail gracefully)
# ============================================================================

log_info "[COMM] /testcommand (should not work)"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/testcommand" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# The agent should handle the missing command gracefully
if [[ "$result_clean" == *"Unknown"* ]] || [[ "$result_clean" == *"command"* ]]; then
    log_pass "Agent handles missing command gracefully"
else
    log_warn "Result for missing command: ${result_clean:0:100}"
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
