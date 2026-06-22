#!/bin/bash
# @group: 9
# @name: tmux_nano_edit_file
# @tags: fast
# @timeout: 90
# @description: Agent uses nano to create/edit file - verify via side-effect

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=2
export TEST_TAGS=("fast")
export TEST_TIMEOUT=90

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.2_tmux_nano_edit_file"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing sessions with this pattern
tmux kill-session -t test-nano-$$ 2>/dev/null || true
rm -f /tmp/nano-test-$$-file.txt 2>/dev/null || true

# Run agent to use nano to create file
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Use ONLY nano to create /tmp/nano-test-$$-file.txt with content 'nano-created-content'. Do NOT use file_edit or write_file tools - you must use nano interactively in a tmux session. Save with Ctrl+O and exit with Ctrl+X.")

# Verify: File was created with correct content (side-effect)
if expect_file_exists "/tmp/nano-test-$$-file.txt" "File created via nano" "$TEST_NAME"; then
    if expect_file_contains "/tmp/nano-test-$$-file.txt" "nano-created-content" "File contains expected content" "$TEST_NAME"; then
        NANO_SUCCESS=true
    else
        log_fail "File does not contain expected content"
        NANO_SUCCESS=false
    fi
else
    log_fail "File was not created"
    NANO_SUCCESS=false
fi

# Verify: Agent did not use prohibited tools (file_edit/write_file as tools)
USED_PROHIBITED_TOOL=false
if echo "$result" | grep -qi "file_edit.*=.*\"\|write_file.*=.*\""; then
    log_fail "Agent used file_edit or write_file tool instead of nano"
    USED_PROHIBITED_TOOL=true
else
    log_pass "Agent did not use prohibited tools (file_edit/write_file)"
fi

# Verify: Agent used nano
USED_NANO=false
if echo "$result" | grep -qi "nano"; then
    log_pass "Agent mentioned/used nano"
    USED_NANO=true
fi

# Cleanup
rm -f /tmp/nano-test-$$-file.txt 2>/dev/null || true

if $NANO_SUCCESS && ! $USED_PROHIBITED_TOOL && $USED_NANO; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
