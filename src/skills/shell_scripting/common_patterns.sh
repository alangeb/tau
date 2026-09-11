#!/bin/bash
# common_patterns.sh — Shell scripting pattern reference for Tau agent
# Source for quick access: source skills/shell_scripting/common_patterns.sh

# Text processing
text_freq() { sort | uniq -c | sort -rn; }
text_unique() { sort -u; }
text_count() { grep -c "$1" "$2"; }
text_fields() { awk -F'|' "{print \$$1}" "$@"; }
head_json() { python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin),indent=2)[:$1])" 2>/dev/null; }

# File operations
find_py() { find . -name "*.py" -type f "$@"; }
find_large() { find . -name "*.py" -size +100k; }
find_recent() { find . -name "*.py" -mtime -1; }
find_changed() { git diff --name-only HEAD~1 2>/dev/null || git diff --cached --name-only; }
count_lines() { find "$1" -name "*.py" -exec cat {} + | wc -l; }

# Process management
bg_run() { "$@" & echo "PID: $!"; }
pid_alive() { ps -p "$1" > /dev/null 2>&1; }
wait_pid() { wait "$1" 2>/dev/null; echo "Exit: $?"; }

# Quick stats
file_stats() {
    echo "Lines: $(wc -l < "$1")"
    echo "Words: $(wc -w < "$1")"
    echo "Chars: $(wc -c < "$1")"
}

# Audit log helpers (Tau-specific)
audit_tools() { grep -oE "final_name='[^']*" "$1" 2>/dev/null | sed "s/final_name='"// | sort | uniq -c | sort -rn; }
audit_errors() { grep -i "error\|exception\|traceback\|failed" "$1" 2>/dev/null | tail -20; }
audit_sessions() { ls -t "$HOME/.local/tau/log"/*.audit 2>/dev/null | head -10; }

# Directory analysis
dir_tree() { find "$1" -maxdepth 2 -type f | head -50; }
file_sizes() { find "$1" -type f -exec wc -l {} + | sort -rn | head -20; }

# Tmux helpers
tmux_ls() { tmux list-sessions 2>/dev/null | grep "tmux-agent-"; }
tmux_capture() { tmux capture-pane -t "$1" -p -S -30 2>/dev/null; }
tmux_kill() { tmux kill-session -t "$1" 2>/dev/null; }
