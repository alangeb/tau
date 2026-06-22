#!/bin/bash
# @group: 5
# @name: pyscan_encoding_error
# @tags: fast
# @timeout: 30
# @description: Test pyscan handles invalid encoding gracefully in markdown output

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=5
export TEST_SUBGROUP=1
export TEST_INDEX=5
export TEST_TAGS=("fast")
export TEST_TIMEOUT=30

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_5.1.5_pyscan_encoding_error"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Create test project in /tmp
rm -rf /tmp/pyscan_encoding
mkdir -p /tmp/pyscan_encoding

# Create a file with invalid UTF-8 bytes (will be read as latin-1)
printf 'def broken():\n    return \xff\xfe\n' > "/tmp/pyscan_encoding/bad_encoding.py"

# Create a valid file too
cat > "/tmp/pyscan_encoding/good.py" << 'EOF'
def valid(): return "ok"
EOF

# Run pyscan
result=$(cd /tmp && PYTHONPATH=$HOME/tau/src /usr/bin/env python3 -c "
from tools.pyscan import run
print(run(agent=None, path='/tmp/pyscan_encoding'))
")

pass=1

# Check output contains markdown header (should not crash)
if echo "$result" | grep -q "# AI Project Index"; then
    log_pass "Output contains markdown header despite encoding issue"
else
    log_fail "Output missing markdown header"
    pass=0
fi

# Check Total Files is 2
if echo "$result" | grep -q "Total Files:.*2"; then
    log_pass "Total Files is 2"
else
    log_fail "Total Files is not 2"
    pass=0
fi

# Check that bad_encoding.py was analyzed (latin-1 fallback works)
if echo "$result" | grep -q "### File: \`bad_encoding.py\`"; then
    log_pass "bad_encoding.py was analyzed with latin-1 fallback"
else
    log_fail "bad_encoding.py not properly handled"
    pass=0
fi

# Check that good.py was still analyzed
if echo "$result" | grep -q "### File: \`good.py\`"; then
    log_pass "Valid file (good.py) was analyzed"
else
    log_fail "Valid file not analyzed"
    pass=0
fi

# Check valid function exists in good.py
if echo "$result" | grep -q "\[Func\] valid()"; then
    log_pass "valid function found in good.py"
else
    log_fail "valid function not found"
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
rm -rf /tmp/pyscan_encoding

if [[ $pass -eq 1 ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
