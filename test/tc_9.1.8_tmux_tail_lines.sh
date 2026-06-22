#!/bin/bash
# @group: 9
# @name: tmux_tail_lines
# @tags: fast
# @timeout: 60
# @description: Agent tail with specific line count using run_background_tail

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=1
export TEST_INDEX=8
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.1.8_tmux_tail_lines"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing sessions with this pattern
tmux kill-session -t test-tail-$$ 2>/dev/null || true

# Run agent to create session, run commands, tail specific lines
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create a tmux session using run_background_new, then execute: echo a1, echo a2, echo a3, echo a4, echo a5, echo a6, echo a7, echo a8, echo a9, echo a10 using run_background_exec. Then use tail with lines=3 using run_background_tail to get the last 3 lines")

# Verify tail was used and returned limited output (should have a10, a9, a8 - the last 3)
HAS_A10=false
HAS_A9=false
HAS_A8=false

if echo "$result" | grep -q "a10"; then
    HAS_A10=true
    log_pass "Tail output includes a10 (last line)"
fi
if echo "$result" | grep -q "a9"; then
    HAS_A9=true
    log_pass "Tail output includes a9"
fi
if echo "$result" | grep -q "a8"; then
    HAS_A8=true
    log_pass "Tail output includes a8"
fi

if $HAS_A10 && $HAS_A9 && $HAS_A8; then
    TEST_RESULT="PASS"
else
    log_fail "Tail did not return expected last 3 lines"
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
