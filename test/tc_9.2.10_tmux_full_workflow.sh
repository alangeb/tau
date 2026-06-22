#!/bin/bash
# @group: 9
# @name: tmux_full_workflow
# @tags: fast
# @timeout: 90
# @description: Complete tmux workflow - create, edit, read, kill session

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=10
export TEST_TAGS=("fast")
export TEST_TIMEOUT=90

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.10_tmux_full_workflow"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing sessions with this pattern
tmux kill-session -t tmux-agent-workflow-$$ 2>/dev/null || true
rm -f /tmp/workflow-test-$$-file.txt 2>/dev/null || true

# Run agent through complete workflow
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Complete workflow: 1) Create tmux session named tmux-agent-workflow-$$, 2) Execute 'echo workflow-content > /tmp/workflow-test-$$-file.txt', 3) Execute 'cat /tmp/workflow-test-$$-file.txt' to verify, 4) Kill the session")

# Verify 1: File was created during workflow
FILE_CREATED=false
if expect_file_exists "/tmp/workflow-test-$$-file.txt" "File created in workflow" "$TEST_NAME"; then
    FILE_CREATED=true
fi

# Verify 2: File has correct content
CONTENT_CORRECT=false
if expect_file_contains "/tmp/workflow-test-$$-file.txt" "workflow-content" "File has correct content" "$TEST_NAME"; then
    CONTENT_CORRECT=true
fi

# Verify 3: Session was killed at end
SESSION_KILLED=false
if ! tmux ls 2>/dev/null | grep -q "tmux-agent-workflow-$$"; then
    log_pass "Session was killed at end of workflow"
    SESSION_KILLED=true
else
    log_fail "Session still exists after workflow completion"
fi

# Cleanup
rm -f /tmp/workflow-test-$$-file.txt 2>/dev/null || true
tmux kill-session -t tmux-agent-workflow-$$ 2>/dev/null || true

if $FILE_CREATED && $CONTENT_CORRECT && $SESSION_KILLED; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
