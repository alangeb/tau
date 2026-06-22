#!/bin/bash
# @group: 6
# @name: single_tool_call
# @tags: slow
# @timeout: 120
# @description: Verify TOOL_CALLS entry in audit for single tool call

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=6
export TEST_SUBGROUP=0
export TEST_INDEX=4
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
cp "$AGENT_PATH" "$DUT_PATH"
chmod +x "$DUT_PATH"

TEST_NAME="tc_6.0.4_single_tool_call"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Unset TAU_AUDIT_LOG_FILE to ensure audit file is created in LOG_DIR
unset TAU_AUDIT_LOG_FILE

# Run agent with tool-triggering input (with TAU_AUDIT_LOG_FILE unset)
result=$(TAU_AUDIT_LOG_FILE="" timeout "$TEST_TIMEOUT" "$DUT_PATH" "use bash to run: echo 'hello'" 2>&1 | tee -a "$output_file")

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

# Check audit file for TOOL_CALLS entry
if expect_file_contains "$audit_file" "[TOOL_CALLS]" "TOOL_CALLS entry exists" "$TEST_NAME"; then
    # Verify tool call contains expected structure (bash is the tool name)
    if expect_file_contains "$audit_file" '"name": "bash"' "Tool name .bash. in TOOL_CALLS" "$TEST_NAME"; then
        TEST_RESULT="PASS"
    else
        TEST_RESULT="FAIL"
    fi
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
