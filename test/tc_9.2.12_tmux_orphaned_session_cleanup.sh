#!/bin/bash
# @group: 9
# @name: tmux_orphaned_session_cleanup
# @tags: fast
# @timeout: 90
# @description: Verify orphaned sessions can be cleaned up after agent exit

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env"
source "$SCRIPT_DIR/func"

export TEST_GROUP=9
export TEST_SUBGROUP=2
export TEST_INDEX=12
export TEST_TAGS=("fast")
export TEST_TIMEOUT=90

setup_test "$BASH_SOURCE"
    cp "$AGENT_PATH" "$DUT_PATH"

TEST_NAME="tc_9.2.12_tmux_orphaned_session_cleanup"
output_file="./tool_output.txt"
start_time=$(date +%s.%N)

# Clean up any existing orphan-test marker files
rm -f /tmp/orphan-marker-$$-file.txt 2>/dev/null || true

# Run agent to create a session (auto-named tmux-agent-{uuid}), then agent exits (no explicit cleanup)
# Note: run_background tool auto-generates session names as tmux-agent-{uuid}
result=$(run_tool_capture "$output_file" "$TEST_TIMEOUT" "create a new tmux session using run_background_new, then use run_background_exec to run 'echo orphan-test-$$ > /tmp/orphan-marker-$$-file.txt' in that session. Do not kill the session.")

# Verify file was created (proves session ran commands)
MARKER_FILE_EXISTS=false
if expect_file_exists "/tmp/orphan-marker-$$-file.txt" "Orphan marker file created" "$TEST_NAME"; then
    MARKER_FILE_EXISTS=true
fi

# Get all current tmux-agent sessions
ALL_SESSIONS=$(tmux ls 2>/dev/null | grep "tmux-agent-" | cut -d: -f1 || true)
SESSION_COUNT=0
if [[ -n "$ALL_SESSIONS" ]]; then
    SESSION_COUNT=$(echo "$ALL_SESSIONS" | wc -l)
fi

if [[ "$SESSION_COUNT" -gt 0 ]]; then
    log_pass "Found $SESSION_COUNT tmux-agent session(s) to clean up"
    
    # Kill all tmux-agent sessions
    echo "$ALL_SESSIONS" | while read -r session; do
        if [[ -n "$session" && "$session" == tmux-agent-* ]]; then
            tmux kill-session -t "$session" 2>/dev/null || true
        fi
    done
    
    # Small delay for cleanup to complete
    sleep 0.5
    
    # Count sessions after cleanup
    REMAINING_SESSIONS=$(tmux ls 2>/dev/null | grep "tmux-agent-" | wc -l || true)
    REMAINING_SESSIONS=${REMAINING_SESSIONS:-0}
    
    CLEANUP_SUCCESS=false
    if [[ "$REMAINING_SESSIONS" -eq 0 ]]; then
        log_pass "All orphaned sessions cleaned up successfully (remaining=$REMAINING_SESSIONS)"
        CLEANUP_SUCCESS=true
    else
        log_fail "Sessions still exist after cleanup (remaining=$REMAINING_SESSIONS)"
        CLEANUP_SUCCESS=false
    fi
else
    log_pass "No tmux-agent sessions found to clean up"
    CLEANUP_SUCCESS=true
fi

# Verify no orphaned tmux-agent sessions remain
ORPHAN_COUNT=$(tmux ls 2>/dev/null | grep "tmux-agent-" | wc -l || true)
ORPHAN_COUNT=${ORPHAN_COUNT:-0}
if [[ "$ORPHAN_COUNT" -eq 0 ]]; then
    log_pass "No orphaned sessions remaining"
    NO_ORPHANS=true
else
    log_fail "Found $ORPHAN_COUNT orphaned session(s)"
    NO_ORPHANS=false
fi

# Cleanup marker file
rm -f /tmp/orphan-marker-$$-file.txt 2>/dev/null || true

if $MARKER_FILE_EXISTS && $CLEANUP_SUCCESS && $NO_ORPHANS; then
    TEST_RESULT="PASS"
else
    TEST_RESULT="FAIL"
fi

end_time=$(date +%s.%N)
TEST_DURATION=$(awk "BEGIN {printf \"%.2f\", $end_time - $start_time}")

cleanup_test "$BASH_SOURCE"
