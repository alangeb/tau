#!/bin/bash
# @group: 8
# @name: a2a_basic
# @tags: slow
# @timeout: 180
# @description: Test basic A2A connect/query

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=8
export TEST_SUBGROUP=0
export TEST_INDEX=1
export TEST_TAGS=("slow")
export TEST_TIMEOUT=180

setup_test "$BASH_SOURCE"
# Copy AGENT_PATH to DUT_PATH
cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_8.0.1_a2a_basic"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)
AGENT_PID=""

# tau.py is the main executable

# Start agent in background from output directory
log_info "Starting agent..."
"$DUT_PATH" --keep-alive > "$output_file" 2>&1 &
AGENT_PID=$!

# Wait for agent to be ready
log_info "Waiting for agent PID $AGENT_PID to be ready..."
sleep 5

if [[ -z "$AGENT_PID" ]]; then
    log_fail "No active agent found"
    TEST_RESULT="FAIL"
    cleanup_test "$BASH_SOURCE"
    exit 0
fi

# Setup A2A socket
A2A_SOCKET="/tmp/taua2a-${AGENT_PID}.sock"
if [[ ! -S "$A2A_SOCKET" ]]; then
    log_fail "Socket not found: $A2A_SOCKET"
    cleanup_a2a_agent "$AGENT_PID"
    TEST_RESULT="FAIL"
    cleanup_test "$BASH_SOURCE"
    exit 0
fi

log_info "A2A socket ready: $A2A_SOCKET"

# Run A2A query (positional argument instead of --query flag)
log_info "Running A2A query..."
result=$("$DUT_PATH" --pid "$AGENT_PID" "How much is 112233*2 (answer only plain number, no punctuation)?" 2>&1) || true

if echo "$result" | grep -qi "224466"; then
    TEST_RESULT="PASS"
    log_pass "A2A query succeeded"
else
    TEST_RESULT="FAIL"
    log_fail "A2A query failed: $result"
fi

# Cleanup agent
cleanup_a2a_agent "$AGENT_PID"

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
