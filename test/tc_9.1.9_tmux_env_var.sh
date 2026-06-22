#!/bin/bash
# @group: 9
# @name: tmux_env_var
# @tags: fast
# @timeout: 60
# @description: Agent sets and uses env var in tmux session - file verification

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=1
export TEST_INDEX=9
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.1.9_tmux_env_var"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing sessions with this pattern
tmux kill-session -t test-env-$$ 2>/dev/null || true
rm -f /tmp/test-env-output-$$-file.txt 2>/dev/null || true

# Run agent to set env var and write to file
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create a tmux session named test-env-$$, then: 1) execute 'export MYTESTVAR=env-var-value', 2) execute 'echo \$MYTESTVAR > /tmp/test-env-output-$$-file.txt'. Show me the output")

# Verify file contains the env var value (side-effect)
if expect_file_exists "/tmp/test-env-output-$$-file.txt" "File created with env var" "$TEST_NAME"; then
    if expect_file_contains "/tmp/test-env-output-$$-file.txt" "env-var-value" "File contains env var value" "$TEST_NAME"; then
        TEST_RESULT="PASS"
    else
        log_fail "File does not contain expected env var value"
        TEST_RESULT="FAIL"
    fi
else
    TEST_RESULT="FAIL"
fi

# Cleanup
rm -f /tmp/test-env-output-$$-file.txt 2>/dev/null || true

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
