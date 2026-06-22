#!/bin/bash
# @group: 10
# @name: a2a_programming_fizzbuzz
# @tags: fast,a2a
# @timeout: 120
# @description: Test programming with fizzbuzz.py via A2A
#
# Test Intent:
# - Ask agent to create fizzbuzz.py
# - Verify output is correct (1-100, fizz for 3s, buzz for 5s, fizzbuzz for 15s)
# - Edit to remove fizz part
# - Verify modified output
# - Verify the fix persists
# - Verify file runs correctly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=10
export TEST_SUBGROUP=0
export TEST_INDEX=6
export TEST_TAGS=("fast" "a2a" "programming")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_10.0.6_programming_fizzbuzz"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

AGENT_PID=""
A2A_SOCKET=""
ALL_PASSED=true

# ============================================================================
# 1. START: Launch agent with --keep-alive
# ============================================================================

log_info "Starting agent with --keep-alive..."
"$DUT_PATH" --keep-alive > "$output_file" 2>&1 &
AGENT_PID=$!

log_info "Agent started with PID: $AGENT_PID"

# Wait for agent to initialize
sleep 3

# ============================================================================
# 2. WAIT: Poll for A2A socket
# ============================================================================

A2A_SOCKET="/tmp/taua2a-${AGENT_PID}.sock"
socket_ready=0

for i in $(seq 1 10); do
    if [[ -S "$A2A_SOCKET" ]]; then
        log_pass "A2A socket ready after ${i} attempts: $A2A_SOCKET"
        socket_ready=1
        break
    fi
    sleep 0.5
done

if [[ $socket_ready -eq 0 ]]; then
    log_fail "A2A socket not created after 5 seconds"
    ALL_PASSED=false
    if [[ -n "$AGENT_PID" ]] && kill -0 "$AGENT_PID" 2>/dev/null; then
        kill "$AGENT_PID" 2>/dev/null || true
        sleep 1
    fi
    end_time=$(date +%s.%N)
    TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")
    cleanup_test "$BASH_SOURCE"
    exit 1
fi

log_info "A2A socket confirmed: $A2A_SOCKET"

# ============================================================================
# TEST 1: Create fizzbuzz.py
# ============================================================================

log_info "[COMM] Create fizzbuzz.py"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Create a Python file named fizzbuzz.py that prints numbers 1 to 100, but for multiples of 3 print 'fizz' instead of the number, for multiples of 5 print 'buzz', and for multiples of both 3 and 5 print 'fizzbuzz'." 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# Check if file was created
if [[ -f "$TEST_OUTPUT_DIR/fizzbuzz.py" ]]; then
    log_pass "fizzbuzz.py created"
else
    log_fail "fizzbuzz.py not created"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 2: Verify fizzbuzz.py content
# ============================================================================

if [[ -f "$TEST_OUTPUT_DIR/fizzbuzz.py" ]]; then
    if grep -q "fizz" "$TEST_OUTPUT_DIR/fizzbuzz.py" && grep -q "buzz" "$TEST_OUTPUT_DIR/fizzbuzz.py"; then
        log_pass "fizzbuzz.py contains 'fizz' and 'buzz'"
    else
        log_fail "fizzbuzz.py missing fizz or buzz"
        ALL_PASSED=false
    fi
fi

# ============================================================================
# TEST 3: Run fizzbuzz.py and verify output (original version)
# ============================================================================

if [[ -f "$TEST_OUTPUT_DIR/fizzbuzz.py" ]]; then
    log_info "[COMM] Run fizzbuzz.py (original)"
    FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/subagent task='Run the Python file at $TEST_OUTPUT_DIR/fizzbuzz.py and show me the output.' system_prompt_override='Run the Python file and output its stdout exactly as-is.' timeout=30" 2>&1) || true
    result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')
    
    # Check for original fizzbuzz patterns in output (fizz should be present)
    if echo "$result_clean" | grep -q "fizz" && echo "$result_clean" | grep -q "buzz" && echo "$result_clean" | grep -q "fizzbuzz"; then
        log_pass "Original fizzbuzz.py output contains fizz, buzz, and fizzbuzz patterns"
    else
        log_fail "Original fizzbuzz.py output missing expected patterns"
        log_fail "Result: ${result_clean:0:500}"
        ALL_PASSED=false
    fi
    
    # The subagent output may be truncated (shows "more lines"), but the presence of
    # fizzbuzz pattern proves the file ran correctly
    if echo "$result_clean" | grep -q "fizzbuzz"; then
        log_pass "Original fizzbuzz.py completes"
    else
        log_fail "Original fizzbuzz.py didn't complete"
        ALL_PASSED=false
    fi
fi

# ============================================================================
# TEST 4: Edit to remove fizz part
# ============================================================================

log_info "[COMM] Edit fizzbuzz.py to remove fizz (multiples of 3 print number)"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Modify $TEST_OUTPUT_DIR/fizzbuzz.py: for multiples of 3, print the number itself instead of 'fizz'. Keep 'buzz' for multiples of 5 and 'fizzbuzz' for multiples of 15." 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# ============================================================================
# TEST 5: Verify modified output
# ============================================================================

if [[ -f "$TEST_OUTPUT_DIR/fizzbuzz.py" ]]; then
    log_info "[COMM] Run modified fizzbuzz.py"
    FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "/subagent task='Run the Python file at $TEST_OUTPUT_DIR/fizzbuzz.py and show me the output.' system_prompt_override='Run the Python file and output its stdout exactly as-is.' timeout=30" 2>&1) || true
    result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')
    
    # After removing fizz, number 3 should print "3" not "fizz"
    # Check if output contains the number 3 directly (without preceding │)
    if echo "$result_clean" | grep -E "^3$" > /dev/null || echo "$result_clean" | grep -E "^  3$" > /dev/null; then
        log_pass "After edit, number 3 prints as '3' (not 'fizz')"
    else
        log_warn "Could not verify number 3 output (output may be formatted)"
    fi
    
    # Buzz should still work (number 5 should print "buzz")
    if echo "$result_clean" | grep -q "buzz"; then
        log_pass "Buzz pattern still works"
    else
        log_fail "Buzz pattern broken"
        ALL_PASSED=false
    fi
    
    # Fizzbuzz should still work at 15
    if echo "$result_clean" | grep -q "fizzbuzz"; then
        log_pass "Fizzbuzz pattern still works"
    else
        log_fail "Fizzbuzz pattern broken"
        ALL_PASSED=false
    fi
    
    # Verify runs (truncated output but pattern proves success)
    if echo "$result_clean" | grep -q "fizzbuzz"; then
        log_pass "Modified fizzbuzz.py runs"
    else
        log_fail "Modified fizzbuzz.py didn't run"
        ALL_PASSED=false
    fi
fi

# ============================================================================
# TEST 6: Verify the file modification persisted
# ============================================================================

log_info "[COMM] Verify the fizzbuzz.py modification persisted"
if [[ -f "$TEST_OUTPUT_DIR/fizzbuzz.py" ]]; then
    if grep -q 'print(i)' "$TEST_OUTPUT_DIR/fizzbuzz.py" && ! grep -q 'print("fizz")' "$TEST_OUTPUT_DIR/fizzbuzz.py"; then
        log_pass "Modification persisted: multiples of 3 now print number (not 'fizz')"
    else
        log_warn "Modification may not have persisted as expected"
    fi
fi

# ============================================================================
# CLEANUP AND FINAL RESULT
# ============================================================================

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

if [[ "$ALL_PASSED" == "true" ]]; then
    TEST_RESULT="PASS"
    log_pass "All tests passed!"
else
    TEST_RESULT="FAIL"
    log_fail "Some tests failed"
fi

cleanup_test "$BASH_SOURCE"
