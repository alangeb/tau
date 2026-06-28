#!/bin/bash
# context_check.sh — Context capacity monitoring helpers
# Usage: source this file or run individually

# Check context file size
context_size() {
    local context="${1:-~/.local/tau/log/*_2026*_1.context}"
    local bytes=$(wc -c < "$context" 2>/dev/null || echo 0)
    local lines=$(wc -l < "$context" 2>/dev/null || echo 0)
    echo "Context: $bytes bytes, $lines lines"
}

# Estimate token usage (rough: ~4 chars per token)
estimate_tokens() {
    local context="${1:-~/.local/tau/log/*_2026*_1.context}"
    local bytes=$(wc -c < "$context" 2>/dev/null || echo 0)
    local tokens=$(( bytes / 4 ))
    local pct=$(( tokens * 100 / 200000 ))
    echo "Est. tokens: $tokens / 200000 ($pct%)"
    if (( pct > 90 )); then
        echo "CRITICAL: Context near limit — delegate immediately"
    elif (( pct > 80 )); then
        echo "WARNING: Context high — consider compression or delegation"
    fi
}

# Count messages in context
count_messages() {
    local context="${1:-~/.local/tau/log/*_2026*_1.context}"
    local user=$(grep -c '"role": "user"' "$context" 2>/dev/null || echo 0)
    local assistant=$(grep -c '"role": "assistant"' "$context" 2>/dev/null || echo 0)
    local system=$(grep -c '"role": "system"' "$context" 2>/dev/null || echo 0)
    echo "System: $system, User: $user, Assistant: $assistant"
}

# Quick context health check
context_health() {
    local context="${1:-~/.local/tau/log/*_2026*_1.context}"
    echo "=== Context Health ==="
    context_size "$context"
    estimate_tokens "$context"
    count_messages "$context"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-}" in
        size) context_size "$2" ;;
        tokens) estimate_tokens "$2" ;;
        msgs) count_messages "$2" ;;
        health) context_health "$2" ;;
        *) echo "Usage: $0 {size|tokens|msgs|health} [context_file]"; exit 1 ;;
    esac
fi
