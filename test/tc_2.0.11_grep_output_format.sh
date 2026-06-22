#!/bin/bash
# @group: 2
# @name: grep_output_format
# @tags: fast
# @timeout: 60
# @description: Test grep output_format parameter

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=11
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.11_grep_output_format"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Create synthetic test files with KNOWN line numbers
TEST_FILE1="./test_lines.txt"
# 200 lines filler + TARGET at line 201 + 200 more lines
{
    for i in $(seq 1 200); do echo "FILLER_LINE_$i"; done
    echo "NuckChorris"
    for i in $(seq 202 400); do echo "FILLER_LINE_$i"; done
} > "$TEST_FILE1"

TEST_FILE2="./test_context.txt"
# 50 lines filler + TARGET at line 51 + 50 more
{
    for i in $(seq 1 50); do echo "CONTEXT_FILLER_$i"; done
    echo "SEARCH_TARGET"
    for i in $(seq 52 100); do echo "CONTEXT_FILLER_$i"; done
} > "$TEST_FILE2"

TEST_FILE3="./test_default.txt"
# 100 lines filler + TARGET at line 101 + 100 more
{
    for i in $(seq 1 100); do echo "DEFAULT_FILLER_$i"; done
    echo "DEFAULT_PATTERN"
    for i in $(seq 102 200); do echo "DEFAULT_FILLER_$i"; done
} > "$TEST_FILE3"

# Test 1: output_format='lines' - should show filename:line_number:content
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Use your builtin grep() tool, output_format='lines' path='$TEST_FILE1' pattern='NuckChorris'")
pass=1
if echo "$result" | grep -q "test_lines.txt:201:NuckChorris"; then
    log_pass "Lines format correct"
else
    log_fail "Lines format wrong - expected test_lines.txt:201:NuckChorris"
    log_fail "Actual result: $(echo "$result" | grep test_lines.txt | head -1)"
    pass=0
fi

# Test 2: output_format='context' - should show surrounding lines with dashes
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Use your builtin grep() tool, output_format='context' path='$TEST_FILE2' pattern='SEARCH_TARGET'")
# Check for CONTEXT_FILLER_50 with dash format (may have ANSI codes)
if echo "$result" | grep -q "CONTEXT_FILLER_50"; then
    log_pass "Context format correct"
else
    log_fail "Context format wrong - expected CONTEXT_FILLER_50 in context output"
    log_fail "Actual result: $(echo "$result" | grep test_context.txt | head -3)"
    pass=0
fi

# Test 3: Default format (no output_format param)
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Use your builtin grep() tool, path='$TEST_FILE3' pattern='DEFAULT_PATTERN'")
if echo "$result" | grep -q "test_default.txt:101:DEFAULT_PATTERN"; then
    log_pass "Default format correct"
else
    log_fail "Default format wrong - expected test_default.txt:101:DEFAULT_PATTERN"
    log_fail "Actual result: $(echo "$result" | grep test_default.txt | head -1)"
    pass=0
fi

TEST_RESULT="PASS"
if [[ $pass -ne 1 ]]; then
    TEST_RESULT="FAIL"
fi
end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
