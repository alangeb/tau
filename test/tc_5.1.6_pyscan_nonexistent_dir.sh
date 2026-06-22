#!/bin/bash
# @group: 5
# @name: pyscan_nonexistent_dir
# @tags: fast
# @timeout: 30
# @description: Test pyscan returns error message for invalid path

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=5
export TEST_SUBGROUP=1
export TEST_INDEX=6
export TEST_TAGS=("fast")
export TEST_TIMEOUT=30

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_5.1.6_pyscan_nonexistent_dir"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Run pyscan on nonexistent directory
result=$(cd /tmp && PYTHONPATH=$HOME/tau/src /usr/bin/env python3 -c "
from tools.pyscan import run
print(run(agent=None, path='/tmp/nonexistent_directory_xyz'))
")

pass=1

# Check output contains error message (should indicate directory not found)
if echo "$result" | grep -qi "not found\|no such\|does not exist\|error"; then
    log_pass "Error message indicates directory not found"
else
    log_fail "Error message not informative"
    pass=0
fi

# Check no file sections are listed
if echo "$result" | grep -q "### File:"; then
    log_fail "Should not have any files listed for nonexistent dir"
    pass=0
else
    log_pass "No files listed (as expected)"
fi

if [[ $pass -eq 1 ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
