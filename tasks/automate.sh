#!/bin/bash
# ============================================================================
# TASK AUTOMATION HARNESS
# ============================================================================
#
# Loop: pick first .md from 1_todo/ → move to 2_inprogress/ → agent implements
# → agent moves file to 3_done/ or 3_failed/ → repeat until 1_todo/ is empty
#
# ============================================================================

set -eo pipefail

# Configuration
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODE_DIR="$(dirname "${BASE_DIR}")"

TODO_DIR="${BASE_DIR}/1_todo"
INPROGRESS_DIR="${BASE_DIR}/2_inprogress"
DONE_DIR="${BASE_DIR}/3_done"
FAILED_DIR="${BASE_DIR}/3_failed"
LOG_DIR="${BASE_DIR}/log"

# Agent configuration
AGENT="${HOME}/.local/tau/tau.py"
LLM="--llm spark-nothink"
TIMEOUT="${TIMEOUT:-3600}"

# Create directories if they don't exist
mkdir -p "${TODO_DIR}" "${INPROGRESS_DIR}" "${DONE_DIR}" "${FAILED_DIR}" "${LOG_DIR}"

# ============================================================================
# Signal handling: clean up on interrupt
# ============================================================================
cleanup() {
    wait 2>/dev/null || true
    echo ""
    echo "Interrupted — remaining tasks will be recovered on next run."
    exit 1
}
trap cleanup INT TERM

# ============================================================================
# Cleanup: move anything in 2_inprogress back to 1_todo
# ============================================================================
echo "Cleaning up in-progress tasks..."
shopt -s nullglob
for f in "${INPROGRESS_DIR}"/*.md; do
    mv "$f" "${TODO_DIR}/"
    echo "  Moved $(basename "$f") back to 1_todo/"
done
shopt -u nullglob

# ============================================================================
# Main loop
# ============================================================================

while true; do
    # Find first .md file in 1_todo/ (lexicographic order)
    TASK_FILE=$(find "${TODO_DIR}" -maxdepth 1 -name "*.md" -type f 2>/dev/null | sort | head -1)

    if [ -z "${TASK_FILE}" ]; then
        echo "No more tasks in 1_todo/. Done."
        break
    fi

    TASK_NAME=$(basename "${TASK_FILE}")
    echo "========================================"
    echo "Processing: ${TASK_NAME}"
    echo "========================================"

    # Move task from 1_todo/ to 2_inprogress/
    mv "${TASK_FILE}" "${INPROGRESS_DIR}/${TASK_NAME}"

    # Invoke the agent from the code directory
    cd "${CODE_DIR}"

    # Ensure git is clean BEFORE agent runs.
    # We deliberately reset to a known-good state: the agent may leave partial
    # changes, untracked files, or modified state. A clean slate ensures each
    # task starts from the same baseline. We use a named stash so we can
    # safely drop only our own stash without risking unrelated developer work.
    echo "  Cleaning git state before agent..."
    git stash push -u -m "automate_before_$$" 2>/dev/null && git stash drop 2>/dev/null || true

    timeout "${TIMEOUT}" ${AGENT} ${LLM} \
        "/pyprep" \
        "/implement read and perform/execute instructions from file ${INPROGRESS_DIR}/${TASK_NAME}." \
        "If instructions from ${INPROGRESS_DIR}/${TASK_NAME} were successfully executed, move file ${INPROGRESS_DIR}/${TASK_NAME} to folder ${DONE_DIR}, if unsuccessful move file to ${FAILED_DIR}" \
        | tee "${LOG_DIR}/${TASK_NAME%.md}.log" \
        || true

    # Ensure git is clean AFTER agent runs.
    # Same rationale as before: failed runs leave partial state. We need a
    # clean, known-good baseline for the next iteration.
    echo "  Cleaning git state after agent..."
    git stash push -u -m "automate_after_$$" 2>/dev/null && git stash drop 2>/dev/null || true

    # Check where the file ended up
    if [ -f "${DONE_DIR}/${TASK_NAME}" ]; then
        echo "✓ ${TASK_NAME} → 3_done/"
    elif [ -f "${FAILED_DIR}/${TASK_NAME}" ]; then
        echo "✗ ${TASK_NAME} → 3_failed/"
    else
        # Agent timed out, crashed, or didn't move the file
        if [ -f "${INPROGRESS_DIR}/${TASK_NAME}" ]; then
            mv "${INPROGRESS_DIR}/${TASK_NAME}" "${FAILED_DIR}/${TASK_NAME}"
        elif [ -f "${TODO_DIR}/${TASK_NAME}" ]; then
            mv "${TODO_DIR}/${TASK_NAME}" "${FAILED_DIR}/${TASK_NAME}"
        else
            echo "⚠ ${TASK_NAME}: file disappeared, skipping"
        fi
        echo "✗ ${TASK_NAME} → 3_failed/ (harness fallback)"
    fi
done

# Final cleanup: anything remaining in 2_inprogress/ → 1_todo/ (recoverable)
# Files in 1_todo/ are left alone — they'll be picked up on the next run.
echo ""
echo "Final cleanup..."
shopt -s nullglob
for f in "${INPROGRESS_DIR}"/*.md; do
    mv "$f" "${TODO_DIR}/"
    echo "  Moved $(basename "$f") → 1_todo/ (recovered)"
done
shopt -u nullglob

echo "Automation complete."
