#!/bin/bash
# @group: 8
# @name: a2a_context
# @tags: slow
# @timeout: 180
# @description: Test A2A context preservation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=8
export TEST_SUBGROUP=0
export TEST_INDEX=2
export TEST_TAGS=("slow")
export TEST_TIMEOUT=180

setup_test "$BASH_SOURCE"
# Copy AGENT_PATH to DUT_PATH
cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_8.0.2_a2a_context"
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
sleep 2

if [[ -z "$AGENT_PID" ]]; then
    log_fail "No active agent found"
    TEST_RESULT="FAIL"
    cleanup_test "$BASH_SOURCE"
    exit 0
fi

# Run A2A queries (positional argument)
log_info "First query..."
result1=$("$DUT_PATH" --pid "$AGENT_PID" "Remember: X=112233" 2>&1) || true

log_info "Second query..."
result2=$("$DUT_PATH" --pid "$AGENT_PID" --timeout 60 "What is X?" 2>&1) || true

if echo "$result2" | grep -qi "112233"; then
    TEST_RESULT="PASS"
    log_pass "Context preserved across queries"
else
    TEST_RESULT="FAIL"
    log_fail "Context not preserved: $result2"
fi

cleanup_a2a_agent "$AGENT_PID"

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
