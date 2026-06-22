#!/bin/bash
# @group: 8
# @name: a2a_timeout
# @tags: slow
# @timeout: 180
# @description: Test A2A timeout handling

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=8
export TEST_SUBGROUP=0
export TEST_INDEX=5
export TEST_TAGS=("slow")
export TEST_TIMEOUT=180

setup_test "$BASH_SOURCE"
# Copy AGENT_PATH to DUT_PATH
cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_8.0.5_a2a_timeout"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)
AGENT_PID=""

# tau.py is the main executable

# Start agent from output directory
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

# Query with timeout
log_info "Testing timeout..."
result=$(timeout 30 "$DUT_PATH" --pid "$AGENT_PID" "hello" 2>&1) || true

# Should complete successfully
if [[ -n "$result" ]] && echo "$result" | grep -qi "hello\|response\|context"; then
    TEST_RESULT="PASS"
    log_pass "Query completed successfully"
else
    TEST_RESULT="FAIL"
    log_fail "Unexpected result: $result"
fi

cleanup_a2a_agent "$AGENT_PID"

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
