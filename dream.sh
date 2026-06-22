#!/bin/bash
# dream.sh — Endless loop: invoke tau.py with "/_dream" prompt
# Can be invoked from any directory; cd's into src/ automatically.

# Configuration (customize as needed)
TAU_BIN="./tau.py"
LLM_GROUP="--llm spark"
TAU_CMD="${TAU_BIN} ${LLM_GROUP}"
PROMPT="/_dream When running tau run with --llm spark (like: tau --llm spark)"

# Resolve src/ relative to this script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/src" || exit 1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "dreaming... (cwd: $(pwd))"
log "Command: ${TAU_CMD} ${PROMPT}"

while true; do
    log "--- new cycle ---"
    ${TAU_CMD} "${PROMPT}"
    log "--- cycle done ---"
done
