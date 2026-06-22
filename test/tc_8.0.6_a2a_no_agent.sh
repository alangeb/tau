#!/bin/bash
# @group: 8
# @name: a2a_no_agent
# @tags: slow
# @timeout: 180
# @description: Test A2A when no agent is running

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=8
export TEST_SUBGROUP=0
export TEST_INDEX=6
export TEST_TAGS=("slow")
export TEST_TIMEOUT=180

setup_test "$BASH_SOURCE"
# Copy AGENT_PATH to DUT_PATH
cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_8.0.6_a2a_no_agent"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# tau.py is the main executable

# Clean up any stale sockets
rm -f /tmp/taua2a-*.sock 2>/dev/null || true

# Query non-existent agent - should fail gracefully
log_info "Querying non-existent agent..."
result=$("$DUT_PATH" --pid 99999 "test" 2>&1) || true

# Should fail with error about agent not found
if echo "$result" | grep -qi "error\|not found\|no agent"; then
    TEST_RESULT="PASS"
    log_pass "Graceful failure when no agent"
else
    TEST_RESULT="FAIL"
    log_fail "Should fail gracefully: $result"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
