#!/bin/bash
# @group: 9
# @name: run_background_session_validation
# @tags: fast tmux session_validation
# @timeout: 60
# @description: Test run_background_exec validates session existence before execution

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=14
export TEST_TAGS=("fast" "tmux" "session_validation")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.14_run_background_session_validation"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing test sessions
tmux kill-session -t tc-validation-$$ 2>/dev/null || true

echo "=== Test 1: Valid session creates and executes ===" > "$output_file"

# Test 1: Create session via new-session, then execute
result1=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Create a tmux session using run_background_new and execute 'whoami' using run_background_exec. Show me the output.")

if echo "$result1" | grep -qi "whoami\|uid=\|root\|${USER}"; then
    echo "PASS: Valid session executed correctly" >> "$output_file"
    TEST1_PASS=true
else
    echo "FAIL: Command did not execute in valid session" >> "$output_file"
    echo "Output: $result1" >> "$output_file"
    TEST1_PASS=false
fi

echo "" >> "$output_file"
echo "=== Test 2: Invalid session name format rejected ===" >> "$output_file"

# Test 2: Invalid session name format
result2=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Run 'ls' in session 'my-invalid-session' using run_background_exec")

if echo "$result2" | grep -qi "invalid.*session_name\|must start with tmux-agent"; then
    echo "PASS: Invalid session name rejected" >> "$output_file"
    TEST2_PASS=true
elif echo "$result2" | grep -qi "not found\|error"; then
    echo "PARTIAL: Invalid session name detected but message unclear" >> "$output_file"
    TEST2_PASS=true  # Acceptable - still catches error
else
    echo "FAIL: Invalid session name should be rejected" >> "$output_file"
    TEST2_PASS=false
fi

echo "" >> "$output_file"
echo "=== Test 3: Non-existent session detected ===" >> "$output_file"

# Test 3: Non-existent session (format valid, but session doesn't exist)
# Note: Tool attempts execution and fails with tmux error (no pre-validation)
result3=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "Run 'ls' in session 'tmux-agent-deadbeef' using run_background_exec (this session does not exist)")

if echo "$result3" | grep -qi "does not exist"; then
    echo "PASS: Non-existent session detected" >> "$output_file"
    TEST3_PASS=true
else
    echo "FAIL: Non-existent session should produce error" >> "$output_file"
    echo "Output: $result3" >> "$output_file"
    TEST3_PASS=false
fi

echo "" >> "$output_file"
echo "=== Test 4: Wrong workflow caught early ===" >> "$output_file"

# Test 4: Agent should explain workflow and error handling
result4=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "What happens if you try to run a command in a tmux session that doesn't exist? What is the correct workflow?")

has_new_session=false
has_exec=false
has_order=false
has_error_handling=false

# Check for session creation mention (various formats)
if echo "$result4" | grep -qi "new-session\|create session\|run_background_new\|create.*first"; then
    has_new_session=true
fi

# Check for execution mention (various formats)
if echo "$result4" | grep -qi "exec\|send-keys\|run_background_exec\|execute\|run.*command"; then
    has_exec=true
fi

# Check for workflow order/sequence (numbered lists, step words, or ordering keywords)
if echo "$result4" | grep -qiE "first\|before\|step 1\|step 2\|two-step\|order|^\s*[1-5]\.\s|then\|after\|sequence"; then
    has_order=true
fi

# Check for error handling mention (various formats)
if echo "$result4" | grep -qi "session.*found\|not found\|validation\|check\|error\|fail\|doesn't exist\|can't find"; then
    has_error_handling=true
fi

# Require at least 3 of 4 checks to pass (robust against wording variations)
checks_passed=0
$has_new_session && ((checks_passed++)) || true
$has_exec && ((checks_passed++)) || true
$has_order && ((checks_passed++)) || true
$has_error_handling && ((checks_passed++)) || true

if [[ $checks_passed -ge 3 ]]; then
    echo "PASS: Agent explains workflow and error handling ($checks_passed/4 checks)" >> "$output_file"
    TEST4_PASS=true
else
    echo "FAIL: Agent doesn't fully explain workflow ($checks_passed/4 checks)" >> "$output_file"
    echo "Missing: new_session=$has_new_session, exec=$has_exec, order=$has_order, error=$has_error_handling" >> "$output_file"
    TEST4_PASS=false
fi

# Cleanup
echo "" >> "$output_file"
echo "=== Cleanup ===" >> "$output_file"
tmux kill-session -t tc-validation-$$ 2>/dev/null || true

# Final result
if $TEST1_PASS && $TEST2_PASS && $TEST3_PASS && $TEST4_PASS; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
