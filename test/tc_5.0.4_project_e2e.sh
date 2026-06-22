#!/bin/bash
# @group: 5
# @name: project_e2e
# @tags: slow
# @timeout: 180
# @description: Test end-to-end project setup via side effects

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=5
export TEST_SUBGROUP=0
export TEST_INDEX=4
export TEST_TAGS=("slow")
export TEST_TIMEOUT=180

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_5.0.4_project_e2e"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

project_dir="./e2e_project"
mkdir -p "$project_dir"

# Ask agent to create complete Python project
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create a complete Python project in '$project_dir' with README.md, main.py, and requirements.txt")

# Check side effects: files actually exist
pass=1
expect_file_exists "$project_dir/README.md" "README.md created" "$TEST_NAME" || pass=0
expect_file_exists "$project_dir/main.py" "main.py created" "$TEST_NAME" || pass=0
expect_file_exists "$project_dir/requirements.txt" "requirements.txt created" "$TEST_NAME" || pass=0

if [[ $pass -eq 1 ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
