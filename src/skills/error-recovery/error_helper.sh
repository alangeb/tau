#!/bin/bash
# error_helper.sh — Common error recovery patterns
# Usage: source this file or run individually

# Count tool errors in audit log
count_errors() {
    local audit="${1:-~/.local/tau/log/*_2026*_1.audit}"
    local errors=$(grep -c 'TOOL_ERROR' "$audit" 2>/dev/null || echo 0)
    local blocked=$(grep -c 'TOOL_BLOCKED' "$audit" 2>/dev/null || echo 0)
    echo "TOOL_ERROR: $errors, TOOL_BLOCKED: $blocked"
}

# List error types
list_errors() {
    local audit="${1:-~/.local/tau/log/*_2026*_1.audit}"
    grep 'TOOL_ERROR' "$audit" 2>/dev/null | grep -oP 'error_type=\K\w+' | sort | uniq -c | sort -rn
}

# Check for loop patterns (repeated tool calls)
check_loops() {
    local audit="${1:-~/.local/tau/log/*_2026*_1.audit}"
    grep -oP "final_name='[^']*" "$audit" 2>/dev/null | sed "s/final_name='"// | uniq -c | sort -rn | head -10
}

# Find last successful tool call
last_success() {
    local audit="${1:-~/.local/tau/log/*_2026*_1.audit}"
    grep 'TOOL_RESULT.*status=success' "$audit" 2>/dev/null | tail -1
}

# Exponential backoff wait
backoff_wait() {
    local max="${1:-60}"
    local delay=1
    while (( delay <= max )); do
        sleep "$delay"
        delay=$(( delay * 2 ))
    done
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-}" in
        count) count_errors "$2" ;;
        list) list_errors "$2" ;;
        loops) check_loops "$2" ;;
        last) last_success "$2" ;;
        *) echo "Usage: $0 {count|list|loops|last} [audit_file]"; exit 1 ;;
    esac
fi
