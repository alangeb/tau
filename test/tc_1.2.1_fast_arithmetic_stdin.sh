#!/bin/bash
# @group: 1
# @name: fast_arithmetic_stdin
# @tags: fast
# @timeout: 15
# @description: Test basic arithmetic calculation using stdin input mode (INTERACTIVE MODE)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=2
export TEST_INDEX=1
export TEST_TAGS=("fast")
export TEST_TIMEOUT=15

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_1.2.1_fast_arithmetic_stdin"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Run agent with stdin input (interactive mode)
result=$(echo -e "lets do some math, step by step. first let X=37\nnow calculate X=X+42\nnow calculate X=X*13\nBased on previous steps, what is the value of X (reply only the number, no formatting, no dots)?" | timeout "$TEST_TIMEOUT" "$DUT_PATH" 2>&1 | tee "$output_file")

if echo "$result" | grep -q "1027"; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
