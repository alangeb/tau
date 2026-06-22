#!/bin/bash
# @group: 5
# @name: pyscan_single_file
# @tags: fast
# @timeout: 30
# @description: Test pyscan on single Python file extracts class/function info in markdown

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=5
export TEST_SUBGROUP=1
export TEST_INDEX=2
export TEST_TAGS=("fast")
export TEST_TIMEOUT=30

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_5.1.2_pyscan_single_file"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Create test project in /tmp to avoid long path issues
rm -rf /tmp/pyscan_single
mkdir -p /tmp/pyscan_single
cat > "/tmp/pyscan_single/main.py" << 'EOF'
import os
class Proc:
    def init(self): pass
def main(): pass
EOF

# Run pyscan - use direct tool call to avoid agent truncation
result=$(cd /tmp && PYTHONPATH=$HOME/tau/src /usr/bin/env python3 -c "
from tools.pyscan import run
print(run(agent=None, path='/tmp/pyscan_single'))
")

pass=1

# Check markdown header exists
if echo "$result" | grep -q "# AI Project Index"; then
    log_pass "Output contains markdown header"
else
    log_fail "Output missing markdown header"
    pass=0
fi

# Check Total Files is 1
if echo "$result" | grep -q "Total Files:.*1"; then
    log_pass "Total Files is 1"
else
    log_fail "Total Files is not 1"
    pass=0
fi

# Check main.py file section exists
if echo "$result" | grep -q "### File: \`main.py\`"; then
    log_pass "main.py file section found"
else
    log_fail "main.py file section not found"
    pass=0
fi

# Check Proc class exists
if echo "$result" | grep -q "\[Class\] Proc"; then
    log_pass "Proc class found"
else
    log_fail "Proc class not found"
    pass=0
fi

# Check Proc has method: init
if echo "$result" | grep -q "init(self)"; then
    log_pass "Proc has init method"
else
    log_fail "Proc missing expected method"
    pass=0
fi

# Check main function exists
if echo "$result" | grep -q "\[Func\] main()"; then
    log_pass "main function found"
else
    log_fail "main function not found"
    pass=0
fi

# Check Project Summary exists
if echo "$result" | grep -q "## Project Summary"; then
    log_pass "Project Summary section exists"
else
    log_fail "Project Summary section missing"
    pass=0
fi

# Cleanup
rm -rf /tmp/pyscan_single

if [[ $pass -eq 1 ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
