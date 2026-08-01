#!/bin/bash
# session_helpers.sh — Tmux background session management utilities
# Usage: source this file or run directly: ./session_helpers.sh <command>

set -euo pipefail

# List agent sessions with status (attached/detached, pane count)
bg_list() {
    tmux list-sessions -F '#{session_name}: #{session_attached} attached, #{session_windows} panes' 2>/dev/null \
        | grep 'tmux-agent-' || echo "No agent sessions found"
}

# Capture output from a session
# Usage: bg_output <session_name> [lines]
bg_output() {
    local session="${1:?Usage: bg_output <session> [lines]}"
    local lines="${2:-30}"
    if ! tmux has-session -t "$session" 2>/dev/null; then
        echo "Session '$session' not found" >&2; return 1
    fi
    tmux capture-pane -t "$session" -p -S -"$lines"
}

# Wait for keywords in session output with polling
# Usage: bg_await <session> <keywords_regex> [timeout_s] [poll_interval_s]
bg_await() {
    local session="${1:?Usage: bg_await <session> <keywords> [timeout] [interval]}"
    local keywords="${2:?Keywords required}"
    local timeout="${3:-120}"
    local interval="${4:-5}"
    local elapsed=0
    while (( elapsed < timeout )); do
        if ! tmux has-session -t "$session" 2>/dev/null; then
            echo "SESSION DEAD: $session"; return 1
        fi
        local output
        output=$(tmux capture-pane -t "$session" -p -S -50 2>/dev/null)
        if echo "$output" | grep -qE "$keywords"; then
            echo "KEYWORD MATCH after ${elapsed}s"
            echo "$output" | tail -20
            return 0
        fi
        sleep "$interval"
        elapsed=$((elapsed + interval))
    done
    echo "TIMEOUT after ${timeout}s"
    return 1
}

# Create a new tmux agent session
# Usage: bg_create [command]
bg_create() {
    local cmd="${1:-bash}"
    local name
    name=$(tmux new-session -d -s 'tmux-agent-XXXX' "$cmd" 2>&1 | awk '{print $2}' | cut -d: -f1)
    # Fallback: list sessions and find the newest
    if [[ -z "$name" || "$name" == *"'"* ]]; then
        name=$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep 'tmux-agent-' | tail -1)
    fi
    echo "Created: $name"
    echo "$name"
}

# Show status of all agent sessions with recent output
bg_status() {
    echo "=== Agent Sessions ==="
    bg_list
    echo ""
    for session in $(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep tmux-agent-); do
        echo "--- $session (last 5 lines) ---"
        tmux capture-pane -t "$session" -p -S -5 2>/dev/null
        echo ""
    done
}

# Cleanup all agent sessions
bg_cleanup() {
    local count=0
    for session in $(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep tmux-agent-); do
        tmux kill-session -t "$session" 2>/dev/null && ((count++)) || true
    done
    echo "Killed $count agent session(s)"
}

# Show usage
bg_help() {
    cat <<'EOF'
Tmux Background Session Helpers
Usage: source session_helpers.sh  # then use functions
   or: ./session_helpers.sh <command> [args]

Commands:
  list                    List agent sessions
  output <session> [N]   Show last N lines (default 30)
  await <session> <kw>   Wait for keyword match (regex)
  create [command]        Create new agent session
  status                  Show all sessions with output
  cleanup                 Kill all agent sessions
  help                    Show this help
EOF
}

# CLI entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    cmd="${1:-help}"
    shift || true
    case "$cmd" in
        list)     bg_list "$@" ;;
        output)   bg_output "$@" ;;
        await)    bg_await "$@" ;;
        create)   bg_create "$@" ;;
        status)   bg_status "$@" ;;
        cleanup)  bg_cleanup "$@" ;;
        help|--help|-h) bg_help ;;
        *) echo "Unknown: $cmd. Run: $0 help" >&2; exit 1 ;;
    esac
fi
