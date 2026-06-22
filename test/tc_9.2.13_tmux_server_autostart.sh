#!/bin/bash
# @group: 9
# @name: tmux_server_autostart
# @tags: fast
# @timeout: 60
# @description: Agent works even when tmux server is not running

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=13
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.13_tmux_server_autostart"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Kill all tmux servers
tmux kill-server 2>/dev/null || true
sleep 1

# Run agent to create session (should auto-start server)
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create a new tmux session")

# Assertions
session_found=false
created_found=false
if [[ "$result" == *"session"* ]]; then
    session_found=true
fi
if [[ "$result" == *"Created"* ]] || [[ "$result" == *"created"* ]]; then
    created_found=true
fi
if $session_found && $created_found; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
