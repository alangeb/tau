#!/bin/bash
# @group: 9
# @name: tmux_vi_edit_file
# @tags: fast
# @timeout: 90
# @description: Agent uses vi via run_background_send_keys - verify via side-effect

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=1
export TEST_TAGS=("fast")
export TEST_TIMEOUT=90

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.1_tmux_vi_edit_file"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Setup: Create initial file
echo "original content line 1" > ./testfile.txt

# Clean up any existing sessions with this pattern
tmux kill-session -t test-vi-$$ 2>/dev/null || true

# Run agent with explicit vi instruction
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Use ONLY vi to edit ./testfile.txt. Change 'original' to 'modified', save and exit. Do NOT use file_edit or write_file tools - you must use vi interactively in a tmux session.")

# Verify 1: File was modified (side-effect)
if expect_file_contains "./testfile.txt" "modified" "File content changed via vi" "$TEST_NAME"; then
    VI_EDIT_SUCCESS=true
else
    log_fail "File was not modified correctly"
    VI_EDIT_SUCCESS=false
fi

# Verify 2: Agent used vi, not file_edit or write_file tools
# Note: file_read is OK for verification, just not for editing
# The pattern looks for tool call syntax like tool_name(arg="value")
USED_PROHIBITED_TOOL=false
if echo "$result" | grep -qiE 'file_edit\(|file_edit="'; then
    # Check if file_edit was called as a tool
    log_fail "Agent used file_edit tool instead of vi"
    USED_PROHIBITED_TOOL=true
elif echo "$result" | grep -qiE 'write_file\(|write_file="'; then
    # Check if write_file was called as a tool
    log_fail "Agent used write_file tool instead of vi"
    USED_PROHIBITED_TOOL=true
else
    log_pass "Agent did not use prohibited tools (file_edit/write_file)"
fi

# Verify 3: Agent actually used run_background tools with vi
USED_VI=false
if echo "$result" | grep -qi "run_background.*vi\|vi.*run_background"; then
    log_pass "Agent used vi via run_background tools"
    USED_VI=true
elif echo "$result" | grep -qi "new-session.*vi\|exec.*vi"; then
    log_pass "Agent launched vi in tmux session"
    USED_VI=true
fi

# Cleanup
rm -f /tmp/vi-test-$$-file.txt 2>/dev/null || true

if $VI_EDIT_SUCCESS && ! $USED_PROHIBITED_TOOL && $USED_VI; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
