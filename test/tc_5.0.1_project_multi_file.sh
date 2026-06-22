#!/bin/bash
# @group: 5
# @name: project_multi_file
# @tags: slow
# @timeout: 180
# @description: Test multi-file project setup via side effects

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=5
export TEST_SUBGROUP=0
export TEST_INDEX=1
export TEST_TAGS=("slow")
export TEST_TIMEOUT=180

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_5.0.1_project_multi_file"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

project_dir="./project"
mkdir -p "$project_dir"

# Ask agent to create project files
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create project in '$project_dir' with files: main.py, utils.py, config.txt")

# Check side effects: files actually exist
pass=1
expect_file_exists "$project_dir/main.py" "main.py created" "$TEST_NAME" || pass=0
expect_file_exists "$project_dir/utils.py" "utils.py created" "$TEST_NAME" || pass=0
expect_file_exists "$project_dir/config.txt" "config.txt created" "$TEST_NAME" || pass=0

if [[ $pass -eq 1 ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
