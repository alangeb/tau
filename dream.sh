#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SESSION="dream"
PID_FILE="$SCRIPT_DIR/dream.pid"
DREAM_ARGS=()

# ── Help ──
show_help() {
    cat <<EOF
Usage: dream.sh [OPTIONS] [-- dream.py OPTIONS]

Start the Tau self-improvement loop in a background tmux session.

dream.sh options:
  -h, --help          Show this help message and exit
  -a, --attach        Attach to a running dream tmux session
  --status            Show dream running status
  --stop              Gracefully stop a running dream

dream.py options (passed after -- or directly):
  --n N               Number of cycles (0 = infinite, default)
  --llm MODEL         LLM group (default: spark)
  --dry-run           Skip all LLM invocations, simulate everything

Examples:
    ./dream.sh                     # start with defaults (spark, infinite)
    ./dream.sh --llm deepseek     # use deepseek LLM
    ./dream.sh --n 3              # run 3 cycles then stop
    ./dream.sh --dry-run          # simulate without LLM calls
    ./dream.sh --status           # check if dream is running
    ./dream.sh --attach           # attach to running session
    ./dream.sh --stop             # stop gracefully
EOF
    exit 0
}

# ── Parse arguments ──
# dream.sh flags: --attach, --status, --stop
# dream.py flags: everything after --
SEPARATED=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --) SEPARATED=1; shift ;;
        -h|--help) show_help ;;
        -a|--attach)
            if [[ $SEPARATED -eq 1 ]]; then
                DREAM_ARGS+=("$1")
            else
                # Attach to running dream session
                if tmux has-session -t "$SESSION" 2>/dev/null; then
                    tmux attach -t "$SESSION"
                else
                    echo "dream is not running (start with: ./dream.sh --llm spark)"
                    exit 1
                fi
                exit 0
            fi
            shift ;;
        --status)
            if [[ $SEPARATED -eq 1 ]]; then
                DREAM_ARGS+=("$1")
            else
                if tmux has-session -t "$SESSION" 2>/dev/null; then
                    echo "dream is running in tmux session '$SESSION'"
                    tmux list-panes -t "$SESSION" -F '  pane #{pane_index}: #{pane_current_command}'
                else
                    echo "dream is not running"
                fi
                exit 0
            fi
            ;;
        --stop)
            if [[ $SEPARATED -eq 1 ]]; then
                DREAM_ARGS+=("$1")
            else
                # Stop running dream gracefully
                if [ -f "$PID_FILE" ]; then
                    PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
                    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
                        echo "Sending SIGINT to dream.py (PID $PID)..."
                        kill -INT "$PID"
                        echo "Graceful stop requested. Dream will finish current step and exit."
                    else
                        echo "dream.py is not running (stale PID file)"
                        rm -f "$PID_FILE"
                    fi
                else
                    echo "dream is not running"
                fi
                exit 0
            fi
            ;;
        *)
            if [[ $SEPARATED -eq 1 ]]; then
                DREAM_ARGS+=("$1")
            else
                # Try as dream.py flag
                DREAM_ARGS+=("$1")
            fi
            shift ;;
    esac
done

# ── Single-instance enforcement ──
# Check tmux session first
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "dream already running in tmux session '$SESSION'"
    echo "  attach: tmux attach -t $SESSION"
    echo "  monitor: tail -f dream.log"
    exit 1
fi

# Check PID file (catches dream.py running outside tmux)
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        echo "ERROR: dream.py already running (PID $PID)"
        echo "Kill first: kill $PID"
        exit 1
    fi
    # Stale PID file — clean up
    rm -f "$PID_FILE"
fi

# ── Orphan detection (safety net) ──
ORPHANS=$(pgrep -f "dream.py" -o 2>/dev/null || true)
if [ -n "$ORPHANS" ]; then
    echo "ERROR: dream.py running outside tmux (PID: $ORPHANS)"
    echo "Kill first: kill $ORPHANS"
    exit 1
fi

# ── Pre-flight: git clean check (in shell, so errors hit terminal directly) ──
# Only check when not dry-run (matches dream.py logic)
DRY_RUN=0
for arg in "${DREAM_ARGS[@]}"; do
    [[ "$arg" == "--dry-run" ]] && DRY_RUN=1
done

if [[ $DRY_RUN -eq 0 ]]; then
    GIT_STATUS=$(git -C "$SCRIPT_DIR/src" status --porcelain 2>/dev/null || true)
    if [[ -n "$GIT_STATUS" ]]; then
        echo "ERROR: Git not clean. Refusing to start."
        echo "$GIT_STATUS"
        echo ""
        echo "Fix: commit or stash your changes, then retry."
        exit 1
    fi
fi

# ── Launch ──
cd "$SCRIPT_DIR"
DREAM_CMD="python3 ./dream.py"
if [ ${#DREAM_ARGS[@]} -gt 0 ]; then
    DREAM_CMD="$DREAM_CMD ${DREAM_ARGS[*]}"
fi
tmux new-session -d -s "$SESSION" "exec $DREAM_CMD"

# ── Verify dream.py actually started (session didn't die immediately) ──
# Only verify for unbounded runs (--n 0 or no --n flag). Bounded runs may finish quickly.
NEED_VERIFY=1
for arg in "${DREAM_ARGS[@]}"; do
    # If --n is followed by a number > 0, no need to verify
    if [[ "$arg" == "--n" ]]; then
        NEED_VERIFY=0
        break
    fi
done

if [[ $NEED_VERIFY -eq 1 ]]; then
    sleep 2
    if ! tmux has-session -t "$SESSION" 2>/dev/null; then
        # Session died — check if it was a crash or normal exit
        if [ -f "$SCRIPT_DIR/dream.log" ]; then
            if grep -q '\[ERROR\]\|\[CRASH\]' "$SCRIPT_DIR/dream.log"; then
                echo "ERROR: dream.py crashed immediately after launch."
                echo "Last log lines:"
                tail -10 "$SCRIPT_DIR/dream.log"
                exit 1
            fi
            # Session died but no error in log — could be normal (e.g., --n 1 finished)
            # Just warn silently, don't fail
        fi
    fi
fi

echo "dream started in tmux '$SESSION'"
echo "  attach: tmux attach -t $SESSION"
echo "  monitor: tail -f dream.log"