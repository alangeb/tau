#!/bin/bash
# @group: 1
# @name: fast_bash_stdin
# @tags: fast
# @timeout: 60
# @description: Test basic bash command execution using stdin input mode (INTERACTIVE MODE)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=2
export TEST_INDEX=3
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_1.2.3_fast_bash_stdin"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Run agent with stdin input (interactive mode)
result=$(echo "use bash to run: echo 'Hello from stdin bash!'" | timeout "$TEST_TIMEOUT" "$DUT_PATH" 2>&1 | tee "$output_file")

if echo "$result" | grep -q "Hello from stdin bash"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
