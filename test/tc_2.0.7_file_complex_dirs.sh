#!/bin/bash
# @group: 2
# @name: file_complex_dirs
# @tags: slow
# @timeout: 120
# @description: Test agent's ability to construct and run complex bash commands

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=2
export TEST_SUBGROUP=0
export TEST_INDEX=7
export TEST_TAGS=("slow")
export TEST_TIMEOUT=120

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_2.0.7_file_complex_dirs"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

test_dir="./complex_test"
mkdir -p "$test_dir"

# Ask agent to create a complex bash script that:
# 1. Creates nested directory structure
# 2. Creates files with specific content
# 3. Uses piping and loops
# 4. Writes results to output file
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "write a bash script to 'complex_script.sh' that:
1. Creates directories: data/raw, data/processed, reports
2. Creates 3 input files in data/raw with content: 'alpha', 'beta', 'gamma'
3. Uses a for loop to copy files from data/raw to data/processed
4. Uses piping to count total lines across all processed files
5. Writes the count to reports/summary.txt - ensure to only write the number into the file on a single line, nothing else
6. Creates reports/manifest.txt listing all files in data/processed

Execute the script after creating it.")

# Verify side effects
pass=1

# Get current directory (we're in test output dir, agent created files here too)
CURRENT_DIR="$(pwd)"

# Check directory structure (agent creates in current dir)
if [[ -d "$CURRENT_DIR/data/raw" ]]; then
    log_pass "data/raw directory created"
else
    log_fail "data/raw directory created: directory does not exist"
    pass=0
fi

if [[ -d "$CURRENT_DIR/data/processed" ]]; then
    log_pass "data/processed directory created"
else
    log_fail "data/processed directory created: directory does not exist"
    pass=0
fi

if [[ -d "$CURRENT_DIR/reports" ]]; then
    log_pass "reports directory created"
else
    log_fail "reports directory created: directory does not exist"
    pass=0
fi

# Check input files exist (any 3 .txt files)
raw_count=$(ls "$CURRENT_DIR/data/raw"/*.txt 2>/dev/null | wc -l)
if [[ "$raw_count" -ge 3 ]]; then
    : # Good, has 3+ input files
else
    pass=0
fi

# Check processed files exist (same 3 files copied)
processed_count=$(ls "$CURRENT_DIR/data/processed"/*.txt 2>/dev/null | wc -l)
if [[ "$processed_count" -ge 3 ]]; then
    : # Good, has 3+ processed files
else
    pass=0
fi

# Check summary.txt exists and has a number
if expect_file_exists "$CURRENT_DIR/reports/summary.txt" "summary.txt created" "$TEST_NAME"; then
    count=$(cat "$CURRENT_DIR/reports/summary.txt" 2>/dev/null | tr -d '[:space:]')
    if [[ "$count" =~ ^[0-9]+$ ]] && [[ "$count" -gt 0 ]]; then
        : # Good, has valid count
    else
        pass=0
    fi
else
    pass=0
fi

# Check manifest.txt exists and lists files
if expect_file_contains "$CURRENT_DIR/reports/manifest.txt" "txt" "manifest lists files" "$TEST_NAME"; then
    : # Good
else
    pass=0
fi

if [[ $pass -eq 1 ]]; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
