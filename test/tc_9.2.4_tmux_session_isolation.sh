#!/bin/bash
# @group: 9
# @name: tmux_session_isolation
# @tags: fast
# @timeout: 90
# @description: Two tmux sessions in different PWDs using run_background_new

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=4
export TEST_TAGS=("fast")
export TEST_TIMEOUT=90

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.4_tmux_session_isolation"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing tmux-agent sessions
tmux ls 2>/dev/null | grep "tmux-agent-" | cut -d: -f1 | xargs -r tmux kill-session 2>/dev/null || true
rm -f /tmp/iso-a-$$-file.txt /var/tmp/iso-b-$$-file.txt 2>/dev/null || true

# Session A: cd to /tmp and write file
result_a=$(run_tool_capture "$output_file.a" "$TEST_TIMEOUT" "create a new tmux session using run_background_new, list sessions using run_background_ls to get the name, then execute 'cd /tmp && echo isolated-a > iso-a-$$-file.txt' using run_background_exec")

# Session B: cd to /var/tmp and write file (using a new session)
result_b=$(run_tool_capture "$output_file.b" "$TEST_TIMEOUT" "create a new tmux session using run_background_new, list sessions using run_background_ls to get the name, then execute 'cd /var/tmp && echo isolated-b > iso-b-$$-file.txt' using run_background_exec")

# Verify both files exist in their respective directories (side-effect)
FILE_A_IN_TMP=false
FILE_B_IN_VARTMP=false

if expect_file_exists "/tmp/iso-a-$$-file.txt" "Session A file in /tmp" "$TEST_NAME"; then
    FILE_A_IN_TMP=true
fi

if expect_file_exists "/var/tmp/iso-b-$$-file.txt" "Session B file in /var/tmp" "$TEST_NAME"; then
    FILE_B_IN_VARTMP=true
fi

# Verify isolation: Session A's file should NOT be in /var/tmp
ISOLATION_CLEARED=false
if [[ ! -f "/var/tmp/iso-a-$$-file.txt" ]]; then
    log_pass "Session A's file correctly not in /var/tmp (isolation verified)"
    ISOLATION_CLEARED=true
else
    log_fail "Session A's file incorrectly found in /var/tmp"
fi

# Cleanup
rm -f /tmp/iso-a-$$-file.txt /var/tmp/iso-b-$$-file.txt 2>/dev/null || true

if $FILE_A_IN_TMP && $FILE_B_IN_VARTMP && $ISOLATION_CLEARED; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
