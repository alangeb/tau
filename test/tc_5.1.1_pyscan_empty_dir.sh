#!/bin/bash
# @group: 5
# @name: pyscan_empty_dir
# @tags: fast
# @timeout: 30
# @description: Test pyscan on empty directory returns markdown with 0 files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=5
export TEST_SUBGROUP=1
export TEST_INDEX=1
export TEST_TAGS=("fast")
export TEST_TIMEOUT=30

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_5.1.1_pyscan_empty_dir"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Create empty test directory in /tmp to avoid long path issues
rm -rf /tmp/pyscan_test_empty
mkdir -p /tmp/pyscan_test_empty

# Run pyscan on empty directory using direct tool invocation
result=$(cd /tmp && PYTHONPATH=$HOME/tau/src /usr/bin/env python3 -c "
from tools.pyscan import run
print(run(agent=None, path='/tmp/pyscan_test_empty'))
")

pass=1

# Check output contains markdown header
if echo "$result" | grep -q "# AI Project Index"; then
    log_pass "Output contains markdown header"
else
    log_fail "Output missing markdown header"
    pass=0
fi

# Check Total Files is 0
if echo "$result" | grep -q "Total Files:.*0"; then
    log_pass "Total Files is 0"
else
    log_fail "Total Files is not 0"
    pass=0
fi

# Check no files are listed (no "### File:" entries)
if echo "$result" | grep -q "### File:"; then
    log_fail "Should not have any files listed"
    pass=0
else
    log_pass "No files listed (as expected)"
fi

# Check Project Summary exists
if echo "$result" | grep -q "## Project Summary"; then
    log_pass "Project Summary section exists"
else
    log_fail "Project Summary section missing"
    pass=0
fi

# Cleanup
rm -rf /tmp/pyscan_test_empty

if [[ $pass -eq 1 ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
