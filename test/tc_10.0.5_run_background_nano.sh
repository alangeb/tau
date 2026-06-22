#!/bin/bash
# @group: 10
# @name: a2a_run_background_nano
# @tags: fast,a2a
# @timeout: 120
# @description: Test run_background nano editing via A2A
#
# Test Intent:
# - Create test file
# - Instruct agent to use nano via run_background tools
# - Explicitly prohibit file_edit and run_shell_command
# - Verify nano changes are applied correctly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=10
export TEST_SUBGROUP=0
export TEST_INDEX=5
export TEST_TAGS=("fast" "a2a" "tmux")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_10.0.5_run_background_nano"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# SKIP: Test skipped - tmux-based editor testing deprecated
TEST_RESULT="SKIP"
end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")
log_skip "Skipping test - tmux-based editor testing deprecated"
cleanup_test "$BASH_SOURCE"
exit 0
