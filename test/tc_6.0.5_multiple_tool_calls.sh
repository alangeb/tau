#!/bin/bash
# @group: 6
# @name: multiple_tool_calls
# @tags: slow
# @timeout: 120
# @description: Verify TOOL_CALLS entry with multiple tool calls

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=6
export TEST_SUBGROUP=0
export TEST_INDEX=5
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_6.0.5_multiple_tool_calls"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Unset TAU_AUDIT_LOG_FILE to ensure audit file is created in LOG_DIR
unset TAU_AUDIT_LOG_FILE

# First create a file, then read it (should trigger 2 tool calls)
result=$(TAU_AUDIT_LOG_FILE="" timeout "$TEST_TIMEOUT" "$DUT_PATH" "create file 'test.txt' with 'data', then read 'test.txt'" 2>&1 | tee -a "$output_file")

# Find the audit file (created in ~/.local/tau/log/)
audit_file=$(find "$HOME/.local/tau/log/" -name "*.audit" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
if [[ -z "$audit_file" ]] || [[ ! -f "$audit_file" ]]; then
    log_fail "Audit file not found"
    TEST_RESULT="FAIL"
    end_time=$(date +%s.%N)
    TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")
    cleanup_test "$BASH_SOURCE"
    exit 1
fi

# Check audit file
if expect_file_contains "$audit_file" "[TOOL_CALLS]" "TOOL_CALLS entry exists" "$TEST_NAME"; then
    # Should contain both file_write and file_read
    if expect_file_contains "$audit_file" '"name": "file_write"' "file_write in TOOL_CALLS" "$TEST_NAME"; then
        if expect_file_contains "$audit_file" '"name": "file_read"' "file_read in TOOL_CALLS" "$TEST_NAME"; then
            TEST_RESULT="PASS"
        else
            TEST_RESULT="FAIL"
        fi
    else
        TEST_RESULT="FAIL"
    fi
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
