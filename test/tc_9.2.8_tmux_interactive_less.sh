#!/bin/bash
# @group: 9
# @name: tmux_interactive_less
# @tags: fast
# @timeout: 60
# @description: Agent uses less interactively then quits - verify process exited

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=8
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.8_tmux_interactive_less"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Setup: Create file to view with less
echo "line 1" > /tmp/less-test-$$-file.txt
echo "line 2" >> /tmp/less-test-$$-file.txt
echo "line 3" >> /tmp/less-test-$$-file.txt

# Clean up any existing sessions with this pattern
tmux kill-session -t test-less-$$ 2>/dev/null || true

# Run agent to use less and quit
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create a tmux session named test-less-$$, then use less to view /tmp/less-test-$$-file.txt, press 'q' to quit less, then capture the pane to verify less has exited")

# Verify less exited (should not see less prompt or indicator in capture)
LESS_EXITED=true
if echo "$result" | grep -qi "less\|--END--"; then
    # Check if it's just the command name vs still being in less
    if echo "$result" | grep -qi "\[less\]"; then
        log_fail "Still inside less (found [less] indicator)"
        LESS_EXITED=false
    else
        log_pass "Less was used and exited (no active less indicator)"
    fi
else
    log_pass "Less exited cleanly (no less indicators found)"
fi

# Verify we can run another command after less (session is responsive)
result2=$(run_tool_capture "$output_file.2" "$TEST_TIMEOUT" "execute 'echo after-less' in tmux session test-less-$$ and show output")

SESSION_RESPONSIVE=false
if echo "$result2" | grep -qi "after-less"; then
    log_pass "Session responsive after less exited"
    SESSION_RESPONSIVE=true
else
    log_fail "Session not responsive after less"
fi

# Cleanup
rm -f /tmp/less-test-$$-file.txt 2>/dev/null || true

if $LESS_EXITED && $SESSION_RESPONSIVE; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
