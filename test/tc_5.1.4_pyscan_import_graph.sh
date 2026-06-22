#!/bin/bash
# @group: 5
# @name: pyscan_import_graph
# @tags: fast
# @timeout: 30
# @description: Test pyscan detects import dependencies in markdown output

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=5
export TEST_SUBGROUP=1
export TEST_INDEX=4
export TEST_TAGS=("fast")
export TEST_TIMEOUT=30

setup_test "$BASH_SOURCE"
    # Copy AGENT_PATH to DUT_PATH
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_5.1.4_pyscan_import_graph"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Create test project in /tmp
rm -rf /tmp/pyscan_import
mkdir -p /tmp/pyscan_import

cat > "/tmp/pyscan_import/module_a.py" << 'EOF'
import os, json
from collections import defaultdict
class ModuleA:
    def get_data(self): return {"key": "value"}
EOF

cat > "/tmp/pyscan_import/module_b.py" << 'EOF'
import sys
from module_a import ModuleA
def use_module_a(): return ModuleA().get_data()
EOF

cat > "/tmp/pyscan_import/module_c.py" << 'EOF'
def standalone(): return 42
EOF

# Run pyscan
result=$(cd /tmp && PYTHONPATH=$HOME/tau/src /usr/bin/env python3 -c "
from tools.pyscan import run
print(run(agent=None, path='/tmp/pyscan_import'))
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

# Check module_a file section exists
if echo "$result" | grep -q "### File: \`module_a.py\`"; then
    log_pass "module_a.py file section found"
else
    log_fail "module_a.py file section not found"
    pass=0
fi

# Check module_b file section exists
if echo "$result" | grep -q "### File: \`module_b.py\`"; then
    log_pass "module_b.py file section found"
else
    log_fail "module_b.py file section not found"
    pass=0
fi

# Check module_c file section exists
if echo "$result" | grep -q "### File: \`module_c.py\`"; then
    log_pass "module_c.py file section found"
else
    log_fail "module_c.py file section not found"
    pass=0
fi

# Check ModuleA class exists
if echo "$result" | grep -q "\[Class\] ModuleA"; then
    log_pass "ModuleA class found"
else
    log_fail "ModuleA class not found"
    pass=0
fi

# Check use_module_a function exists
if echo "$result" | grep -q "\[Func\] use_module_a"; then
    log_pass "use_module_a function found"
else
    log_fail "use_module_a function not found"
    pass=0
fi

# Check standalone function exists
if echo "$result" | grep -q "\[Func\] standalone"; then
    log_pass "standalone function found"
else
    log_fail "standalone function not found"
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
rm -rf /tmp/pyscan_import

if [[ $pass -eq 1 ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
