#!/bin/bash
# @group: 5
# @name: pyscan_multi_file
# @tags: fast
# @timeout: 30
# @description: Test pyscan on multi-file project produces markdown output

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=5
export TEST_SUBGROUP=1
export TEST_INDEX=3
export TEST_TAGS=("fast")
export TEST_TIMEOUT=30

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_5.1.3_pyscan_multi_file"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Create test project in /tmp
rm -rf /tmp/pyscan_multi
mkdir -p /tmp/pyscan_multi/src
mkdir -p /tmp/pyscan_multi/tests

cat > "/tmp/pyscan_multi/src/main.py" << 'EOF'
from .utils import helper
def main(): return helper("test")
EOF

cat > "/tmp/pyscan_multi/src/utils.py" << 'EOF'
def helper(data): return data.strip()
class Utils:
    def clean(self, s): return s.strip()
EOF

cat > "/tmp/pyscan_multi/tests/test_main.py" << 'EOF'
import pytest
from src.main import main
def test_main(): assert main("  hello  ") == "hello"
EOF

# Run pyscan - use direct tool call to avoid agent truncation
result=$(cd /tmp && PYTHONPATH=$HOME/tau/src /usr/bin/env python3 -c "
from tools.pyscan import run
print(run(agent=None, path='/tmp/pyscan_multi', include_tests=True))
")

pass=1

# Check markdown header exists
if echo "$result" | grep -q "# AI Project Index"; then
    log_pass "Output contains markdown header"
else
    log_fail "Output missing markdown header"
    pass=0
fi

# Check Total Files is 3
if echo "$result" | grep -q "Total Files:.*3"; then
    log_pass "Total Files is 3"
else
    log_fail "Total Files is not 3"
    pass=0
fi

# Check main.py file section exists (path may include directory prefix)
if echo "$result" | grep -q "### File:.*main.py"; then
    log_pass "main.py file section found"
else
    log_fail "main.py file section not found"
    pass=0
fi

# Check utils.py file section exists (path may include directory prefix)
if echo "$result" | grep -q "### File:.*utils.py"; then
    log_pass "utils.py file section found"
else
    log_fail "utils.py file section not found"
    pass=0
fi

# Check test_main.py file section exists (path may include directory prefix)
if echo "$result" | grep -q "### File:.*test_main.py"; then
    log_pass "test_main.py file section found"
else
    log_fail "test_main.py file section not found"
    pass=0
fi

# Check Utils class exists
if echo "$result" | grep -q "\[Class\] Utils"; then
    log_pass "Utils class found"
else
    log_fail "Utils class not found"
    pass=0
fi

# Check helper function exists
if echo "$result" | grep -q "\[Func\] helper"; then
    log_pass "helper function found"
else
    log_fail "helper function not found"
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
rm -rf /tmp/pyscan_multi

if [[ $pass -eq 1 ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
