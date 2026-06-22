#!/bin/bash
# @group: 9
# @name: tmux_capture_scrollback
# @tags: fast
# @timeout: 60
# @description: Agent capture with scrollback using run_background_capture

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=1
export TEST_INDEX=7
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.1.7_tmux_capture_scrollback"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing sessions with this pattern
tmux kill-session -t test-capture-$$ 2>/dev/null || true

# Run agent to create session, run multiple commands, capture with scrollback
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create a tmux session using run_background_new, then execute these commands one by one using run_background_exec: echo line1, echo line2, echo line3, echo line4, echo line5. Then capture the pane with scrollback=10 using run_background_capture")

# Count lines in captured output
LINE_COUNT=$(echo "$result" | grep "line[0-9]" | wc -l)

if [[ "$LINE_COUNT" -ge 5 ]]; then
    log_pass "Capture with scrollback shows $LINE_COUNT lines (expected >= 5)"
    TEST_RESULT="PASS"
else
    log_fail "Capture shows only $LINE_COUNT lines, expected at least 5"
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
