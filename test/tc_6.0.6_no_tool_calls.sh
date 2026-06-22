#!/bin/bash
# @group: 6
# @name: no_tool_calls
# @tags: fast
# @timeout: 60
# @description: Verify NO TOOL_CALLS entry for normal assistant response

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=6
export TEST_SUBGROUP=0
export TEST_INDEX=6
export TEST_TAGS=("fast")
export TEST_TIMEOUT=60

setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_6.0.6_no_tool_calls"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Use explicit audit file path to avoid race conditions with concurrent tests
AUDIT_FILE="$TEST_OUTPUT_DIR/audit.log"

# Simple greeting - should NOT trigger any tool calls
result=$(TAU_AUDIT_LOG_FILE="$AUDIT_FILE" timeout "$TEST_TIMEOUT" "$DUT_PATH" "say hello" 2>&1 | tee -a "$output_file")

# Validate audit file was created
if [[ ! -f "$AUDIT_FILE" ]]; then
    log_fail "Audit file not created at: $AUDIT_FILE"
    TEST_RESULT="FAIL"
    end_time=$(date +%s.%N)
    TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")
    cleanup_test "$BASH_SOURCE"
    exit 1
fi

# Check audit file - should NOT contain TOOL_CALLS
audit_content=$(cat "$AUDIT_FILE")
if expect_not_contains "[TOOL_CALLS]" "$audit_content" "NO TOOL_CALLS entry (expected)" "$TEST_NAME"; then
    # Should still have USER and ASSISTANT
    if expect_file_contains "$AUDIT_FILE" "[USER]" "USER entry exists" "$TEST_NAME"; then
        if expect_file_contains "$AUDIT_FILE" "[ASSISTANT]" "ASSISTANT entry exists" "$TEST_NAME"; then
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
