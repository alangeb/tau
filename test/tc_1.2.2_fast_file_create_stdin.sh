#!/bin/bash
# @group: 1
# @name: fast_file_create_stdin
# @tags: fast
# @timeout: 60
# @description: Test simple file creation using stdin input mode (INTERACTIVE MODE)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=1
export TEST_SUBGROUP=2
export TEST_INDEX=2
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_1.2.2_fast_file_create_stdin"
output_file="./tool_output.txt"
test_file="./hello_stdin.txt"
start_time=$(date +%s.%N)

# Run agent with stdin input (interactive mode)
result=$(echo "create file '$test_file' with content 'Hello World from stdin!'" | timeout "$TEST_TIMEOUT" "$DUT_PATH" 2>&1 | tee "$output_file")

pass=1
echo "$result" | grep -q "Hello World from stdin" || pass=0
[ -f "$test_file" ] || pass=0
content=$(cat "$test_file" 2>/dev/null) || pass=0
[ "$content" = "Hello World from stdin!" ] || pass=0

TEST_RESULT="PASS"
[[ $pass -ne 1 ]] && TEST_RESULT="FAIL"

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
