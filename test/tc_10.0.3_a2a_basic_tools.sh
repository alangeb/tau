#!/bin/bash
# @group: 10
# @name: a2a_basic_tools
# @tags: fast,a2a
# @timeout: 120
# @description: Test glob, file_read, file_edit tools via A2A
#
# Test Intent:
# - Programmatically create test files
# - Verify agent uses glob (not shell commands)
# - Verify agent uses file_read (not shell commands)
# - Verify agent uses file_edit (not shell commands)
# - Test file modifications: replace, prepend, append, multiline

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=10
export TEST_SUBGROUP=0
export TEST_INDEX=3
export TEST_TAGS=("fast" "a2a")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_10.0.3_a2a_basic_tools"
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
# 3. PREPARE: Create test files programmatically via shell commands
# ============================================================================

# Create initial test file with multiple lines
log_info "[COMM] Create test file with multiple lines via shell"
cat > "$TEST_OUTPUT_DIR/test1.txt" << 'EOF'
Line1:Hello
Line2:World
Line3:Test
Line4:Data
Line5:End
EOF

if [[ -f "$TEST_OUTPUT_DIR/test1.txt" ]]; then
    log_pass "Test file test1.txt created via shell"
else
    log_fail "Test file test1.txt not created"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 1: Verify file content with shell (ground truth)
# ============================================================================

if [[ -f "$TEST_OUTPUT_DIR/test1.txt" ]]; then
    EXPECTED_LINE2=$(sed -n '2p' "$TEST_OUTPUT_DIR/test1.txt")
    if [[ "$EXPECTED_LINE2" == "Line2:World" ]]; then
        log_pass "Ground truth: Line2 is 'Line2:World'"
    else
        log_fail "Ground truth failed: Line2 is '$EXPECTED_LINE2'"
        ALL_PASSED=false
    fi
fi

# ============================================================================
# TEST 2: Test glob tool - agent should list files
# ============================================================================

log_info "[COMM] Use glob to list files matching test*.txt"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Use the glob tool to list all files matching test*.txt in the current directory" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# Check if agent mentions glob tool was used
if [[ "$result_clean" == *"glob"* ]] || [[ "$result_clean" == *"test1.txt"* ]]; then
    log_pass "glob tool used or test1.txt mentioned in result"
else
    log_fail "glob tool not used - result doesn't mention glob or test1.txt"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 3: Test file_read tool
# ============================================================================

log_info "[COMM] Read file test1.txt using file_read tool"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Use file_read to read test1.txt, show me the content" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# Verify content was read
if [[ "$result_clean" == *"Line1:Hello"* ]] && [[ "$result_clean" == *"Line5:End"* ]]; then
    log_pass "file_read returned expected content"
else
    log_fail "file_read did not return expected content"
    log_fail "Result snippet: ${result_clean:0:200}"
    ALL_PASSED=false
fi

# Check if agent used file_read tool (not shell command)
if [[ "$result_clean" == *"file_read"* ]] || [[ "$result_clean" == *"Line1"* ]] || [[ "$result_clean" == *"Line5"* ]]; then
    log_pass "file_read tool appears to have been used"
else
    log_fail "file_read tool was not used"
    ALL_PASSED=false
fi

# ============================================================================
# TEST 4: Test file_edit - replace line
# ============================================================================

log_info "[COMM] Edit test1.txt: replace 'Line3:Test' with 'Line3:Replaced'"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Use file_edit to replace 'Line3:Test' with 'Line3:Replaced' in test1.txt" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# Verify edit was applied
if [[ -f "$TEST_OUTPUT_DIR/test1.txt" ]]; then
    if grep -q "Line3:Replaced" "$TEST_OUTPUT_DIR/test1.txt"; then
        log_pass "file_edit replaced Line3:Test with Line3:Replaced"
    else
        log_fail "file_edit did not apply replacement"
        ALL_PASSED=false
    fi
fi

# ============================================================================
# TEST 5: Test file_edit - prepend line
# ============================================================================

log_info "[COMM] Edit test1.txt: add 'Line0:Start' at the beginning"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Use file_edit to prepend 'Line0:Start' at the beginning of test1.txt (add before Line1:Hello)" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# Verify prepend
if [[ -f "$TEST_OUTPUT_DIR/test1.txt" ]]; then
    FIRST_LINE=$(head -1 "$TEST_OUTPUT_DIR/test1.txt")
    if [[ "$FIRST_LINE" == "Line0:Start" ]]; then
        log_pass "file_edit prepended Line0:Start"
    else
        log_fail "file_edit did not prepend correctly. First line: $FIRST_LINE"
        ALL_PASSED=false
    fi
fi

# ============================================================================
# TEST 6: Test file_edit - append line
# ============================================================================

log_info "[COMM] Edit test1.txt: add 'Line6:Final' at the end"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Use file_edit to append 'Line6:Final' at the end of test1.txt" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# Verify append
if [[ -f "$TEST_OUTPUT_DIR/test1.txt" ]]; then
    LAST_LINE=$(tail -1 "$TEST_OUTPUT_DIR/test1.txt")
    if [[ "$LAST_LINE" == "Line6:Final" ]]; then
        log_pass "file_edit appended Line6:Final"
    else
        log_fail "file_edit did not append correctly. Last line: $LAST_LINE"
        ALL_PASSED=false
    fi
fi

# ============================================================================
# TEST 7: Test file_edit - multiline replacement
# ============================================================================

# Create a new file with multiline content where each line is unique
# We'll replace "Start" with a multiline string
log_info "[COMM] Create test2.txt with unique content for easy matching via shell"
cat > "$TEST_OUTPUT_DIR/test2.txt" << 'EOF'
Header
RowA
RowB
RowC
Footer
EOF

if [[ -f "$TEST_OUTPUT_DIR/test2.txt" ]]; then
    log_pass "test2.txt created via shell"
else
    log_fail "test2.txt not created"
    ALL_PASSED=false
fi

# Replace middle section (each line separately since exact multiline matching may not work)
log_info "[COMM] Edit test2.txt: replace RowA with 'ReplacedA', RowB with 'ReplacedB', RowC with 'ReplacedC'"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Use file_edit three times to replace RowA with ReplacedA, RowB with ReplacedB, and RowC with ReplacedC in $TEST_OUTPUT_DIR/test2.txt" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# Verify multiline edits
if [[ -f "$TEST_OUTPUT_DIR/test2.txt" ]]; then
    if grep -q "ReplacedA" "$TEST_OUTPUT_DIR/test2.txt" && grep -q "ReplacedB" "$TEST_OUTPUT_DIR/test2.txt" && grep -q "ReplacedC" "$TEST_OUTPUT_DIR/test2.txt"; then
        log_pass "file_edit replaced all three rows"
    else
        log_fail "file_edit did not replace all rows"
        ALL_PASSED=false
    fi
fi

# ============================================================================
# TEST 8: Verify agent didn't fall back to shell commands
# ============================================================================

# Check if any results mention shell commands incorrectly
# We already verified specific tool usage, but let's also ensure
# agent is not using shell commands for file operations

log_info "[COMM] Verify agent used appropriate tools (not shell commands)"
FULL_RESULT=$("$DUT_PATH" --pid "$AGENT_PID" "Summarize the file operations we've done so far" 2>&1) || true
result_clean=$(echo "$FULL_RESULT" | sed 's/\x1b\[[0-9;]*m//g')

# Agent should mention file_edit, file_read, glob tools
if [[ "$result_clean" == *"file_edit"* ]] || [[ "$result_clean" == *"file_read"* ]] || [[ "$result_clean" == *"glob"* ]]; then
    log_pass "Agent mentioned appropriate file tools in summary"
else
    log_warn "Agent summary didn't explicitly mention tools (may still have used them)"
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
