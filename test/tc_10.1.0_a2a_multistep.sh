#!/bin/bash
# @group: 10
# @name: a2a_multistep
# @tags: fast,a2a
# @timeout: 180
# @description: Multi-step workflow test via A2A
#
# Test Intent:
# - Complete multi-step project setup (calculator library)
# - Test context persistence across turns
# - Validate proper tool usage (file_edit not shell)
# - Test test execution and verification

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=10
export TEST_SUBGROUP=0
export TEST_INDEX=10
export TEST_TAGS=("fast" "a2a" "multistep")
export TEST_TIMEOUT=180

setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_10.1.0_a2a_multistep"
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
# STEP 1: Project setup - Create directory structure
# ============================================================================

log_info "[STEP 1/7] Project setup: Create calculator project"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Create a Python project named 'calculator' with the following structure: create a calculator.py file in the current directory with empty function stubs for add(), subtract(), multiply(), divide(). Also create test_calculator.py with placeholder tests. Return the exact string 'Success' when done." 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

if [[ "$result_clean" == *"success"* ]] || [[ "$result_clean" == *"Success"* ]] || [[ "$result_clean" == *"created"* ]]; then
    log_pass "Project structure created"
else
    log_fail "Project structure creation unclear"
    ALL_PASSED=false
fi

# ============================================================================
# STEP 2: Implement calculator functions
# ============================================================================

log_info "[STEP 2/7] Implement calculator functions"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Implement the calculator functions in calculator.py: add(a,b) returns a+b, subtract(a,b) returns a-b, multiply(a,b) returns a*b, divide(a,b) returns a/b. Use file_edit to modify the file. Ensure proper error handling for division by zero." 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

if [[ -f "$TEST_OUTPUT_DIR/calculator.py" ]]; then
    if grep -q "def add" "$TEST_OUTPUT_DIR/calculator.py" && grep -q "def subtract" "$TEST_OUTPUT_DIR/calculator.py"; then
        log_pass "Calculator functions implemented"
    else
        log_fail "Calculator functions not found"
        ALL_PASSED=false
    fi
else
    log_fail "calculator.py not created"
    ALL_PASSED=false
fi

# ============================================================================
# STEP 3: Run tests
# ============================================================================

log_info "[STEP 3/7] Verify test file structure"
if [[ -f "$TEST_OUTPUT_DIR/calculator.py" ]] && [[ -f "$TEST_OUTPUT_DIR/test_calculator.py" ]]; then
    # Check both files are valid Python
    if /usr/bin/env python3 -m py_compile "$TEST_OUTPUT_DIR/calculator.py" 2>/dev/null && /usr/bin/env python3 -m py_compile "$TEST_OUTPUT_DIR/test_calculator.py" 2>/dev/null; then
        log_pass "Both Python files are valid"
    else
        log_fail "Python syntax error in one of the files"
        ALL_PASSED=false
    fi
else
    log_fail "Test files not created"
    ALL_PASSED=false
fi

# ============================================================================
# STEP 4: Create documentation
# ============================================================================

log_info "[STEP 4/7] Create README.md"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Create a README.md file in the current directory with sections: Title 'Calculator Library', Installation 'Just copy calculator.py', Usage 'from calculator import add, subtract, multiply, divide', Examples showing basic operations, and License 'MIT'." 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

if [[ -f "$TEST_OUTPUT_DIR/README.md" ]]; then
    if grep -q "Calculator Library" "$TEST_OUTPUT_DIR/README.md" && grep -q "Installation" "$TEST_OUTPUT_DIR/README.md"; then
        log_pass "README.md created with expected sections"
    else
        log_fail "README.md missing expected sections"
        ALL_PASSED=false
    fi
else
    log_fail "README.md not created"
    ALL_PASSED=false
fi

# ============================================================================
# STEP 5: Verify tool usage (not shell commands for file ops)
# ============================================================================

log_info "[STEP 5/7] Verify proper tool usage"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Summarize the file operations we've done and which tools were used" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

if [[ "$result_clean" == *"file_edit"* ]] || [[ "$result_clean" == *"write_file"* ]]; then
    log_pass "Agent used file manipulation tools"
else
    log_warn "Tool usage summary unclear (may have used shell commands)"
fi

# ============================================================================
# STEP 6: Test operations
# ============================================================================

log_info "[STEP 6/7] Test basic calculator operations"
if [[ -f "$TEST_OUTPUT_DIR/calculator.py" ]]; then
    FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Import the calculator module and verify: add(2,3)=5, subtract(5,3)=2, multiply(4,5)=20, divide(10,2)=5. Return the results." 2>&1) || true
    result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')
    
    if [[ "$result_clean" == *"5"* ]] && [[ "$result_clean" == *"20"* ]] && [[ "$result_clean" == *"5"* ]]; then
        log_pass "Calculator operations verified"
    else
        log_fail "Calculator operations verification unclear"
        log_fail "Result: ${result_clean:0:200}"
        ALL_PASSED=false
    fi
fi


# ============================================================================
# STEP 7: Challenge - Introduce Bug & Agent Fix
# ============================================================================

log_info "[STEP 7/7] Challenge: Introduce bug and ask agent to fix"

# Introduce a bug: change add(a,b) to return a+b+1 (off-by-one error)

# Inject bug using sed (test harness side, not agent)
if [[ -f "$TEST_OUTPUT_DIR/calculator.py" ]]; then
    # Save original for reference
    cp "$TEST_OUTPUT_DIR/calculator.py" "$TEST_OUTPUT_DIR/calculator.py.orig"
    
    # Inject the bug: replace "return a + b" with "return a + b + 1" in add function
    sed -i '/def add/,/^def /s/return a + b$/return a + b + 1/' "$TEST_OUTPUT_DIR/calculator.py"
    
    # Verify bug was injected
    if grep -q "a + b + 1" "$TEST_OUTPUT_DIR/calculator.py"; then
        log_pass "Bug injected: add() now returns a+b+1 (off-by-one error)"
    else
        log_fail "Failed to inject bug into calculator.py"
        ALL_PASSED=false
    fi
else
    log_fail "calculator.py not found for bug injection"
    ALL_PASSED=false
fi

# Ask the agent to detect and fix the bug
log_info "Asking agent to detect and fix the bug in calculator.py"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "A bug was introduced into calculator.py - the add() function now returns wrong values (off-by-one error). Please inspect the file, identify the bug, and fix it. Use file_edit or write_file to apply the fix." 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# Check if the agent actually fixed the file (check it does NOT have the +1 anymore)
if [[ -f "$TEST_OUTPUT_DIR/calculator.py" ]]; then
    if grep -q "a + b + 1" "$TEST_OUTPUT_DIR/calculator.py"; then
        log_fail "Agent did not fix the bug - file still contains a+b+1"
        ALL_PASSED=false
    else
        log_pass "Agent fixed the bug in calculator.py"
    fi
else
    log_fail "calculator.py missing after fix attempt"
    ALL_PASSED=false
fi

# Verify fix works: test that add(2, 3) == 5
log_info "Verifying fixed calculator operations work correctly"
if [[ -f "$TEST_OUTPUT_DIR/calculator.py" ]]; then
    FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Import calculator.py from $TEST_OUTPUT_DIR/ and verify: add(2,3)=5, subtract(10,4)=6, multiply(3,7)=21. Return the results as numbers only." 2>&1) || true
    result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')
    
    # Check for correct results: 5, 6, 21
    if [[ "$result_clean" == *"5"* ]] && [[ "$result_clean" == *"6"* ]] && [[ "$result_clean" == *"21"* ]]; then
        log_pass "Fixed calculator operations verified (add=5, subtract=6, multiply=21)"
    else
        log_fail "Fixed calculator operations verification unclear"
        log_fail "Result: ${result_clean:0:200}"
        ALL_PASSED=false
    fi
else
    log_fail "calculator.py not found for post-fix verification"
    ALL_PASSED=false
fi

# ============================================================================
# CLEANUP AND FINAL RESULT
# ===========================================================================

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
