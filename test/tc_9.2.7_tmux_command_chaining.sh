#!/bin/bash
# @group: 9
# @name: tmux_command_chaining
# @tags: fast
# @timeout: 60
# @description: Agent chains commands with && in tmux session - verify file in subdirectory

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=7
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.7_tmux_command_chaining"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing sessions with this pattern
tmux kill-session -t test-chain-$$ 2>/dev/null || true
rm -rf /tmp/chain-test-$$ 2>/dev/null || true

# Run agent to chain commands: mkdir && cd && touch
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create a tmux session named test-chain-$$, then execute this chained command: 'mkdir -p /tmp/chain-test-$$/subdir && cd /tmp/chain-test-$$/subdir && touch chained-file.txt'")

# Verify file exists at correct path (side-effect)
if expect_file_exists "/tmp/chain-test-$$/subdir/chained-file.txt" "File created in subdirectory via command chain" "$TEST_NAME"; then
    CHAIN_SUCCESS=true
else
    log_fail "Command chain did not create file in subdirectory"
    CHAIN_SUCCESS=false
fi

# Cleanup
rm -rf /tmp/chain-test-$$ 2>/dev/null || true

if $CHAIN_SUCCESS; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
