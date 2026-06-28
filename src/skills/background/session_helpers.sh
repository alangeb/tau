#!/bin/bash
# background_session.sh — Common tmux background session management patterns
# Usage: source this file or run individual functions

# List active sessions with status
bg_status() {
    tmux list-sessions -F '#{session_name}: #{session_attached} panes' 2>/dev/null | grep tmux-agent-
    echo ""
    for session in $(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep tmux-agent-); do
        echo "--- $session ---"
        tmux capture-pane -t "$session" -p -S -3 2>/dev/null
    done
}

# Cleanup all agent sessions
bg_cleanup() {
    for session in $(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep tmux-agent-); do
        tmux kill-session -t "$session" 2>/dev/null
    done
    echo "All agent sessions killed"
}
