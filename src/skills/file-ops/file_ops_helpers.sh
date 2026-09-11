#!/bin/bash
# file_ops_helpers.sh — Common file operation patterns
# Usage: source skills/file-ops/file_ops_helpers.sh

set -euo pipefail

# Find all files matching pattern, excluding common dirs
fo_find() {
    local pattern="${1:?Usage: fo_find <pattern> [dir]}"
    local dir="${2:-.}"
    find "$dir" -type f -name "$pattern" \
        -not -path '*/.git/*' -not -path '*/__pycache__/*' -not -path '*/node_modules/*' \
        -not -path '*/.venv/*' -not -path '*/venv/*'
}

# Count lines in all matching files
fo_wcl() {
    local pattern="${1:?Usage: fo_wcl <pattern> [dir]}"
    local dir="${2:-.}"
    fo_find "$pattern" "$dir" | xargs wc -l 2>/dev/null | tail -1
}

# List files by size (largest first)
fo_largest() {
    local pattern="${1:?Usage: fo_largest <pattern> [n]}"
    local n="${2:-10}"
    fo_find "$pattern" | xargs ls -lhS 2>/dev/null | head -n "$n"
}

# Find recently modified files (last N hours)
fo_recent() {
    local hours="${1:-24}"
    find . -type f -mmin -$((hours * 60)) \
        -not -path '*/.git/*' -not -path '*/__pycache__/*' | sort
}

# Quick diff of two files with context
fo_diff() {
    local f1="${1:?Usage: fo_diff <file1> <file2>}"
    local f2="${2:?Usage: fo_diff <file1> <file2>}"
    diff -u --color=auto "$f1" "$f2" 2>/dev/null || true
}

# Find duplicate files by content
fo_duplicates() {
    local pattern="${1:-*.py}"
    fo_find "$pattern" | xargs md5sum 2>/dev/null | sort | uniq -D -w 32
}

# Batch rename files (dry run by default)
fo_rename() {
    local from="${1:?Usage: fo_rename <from_pattern> <to_pattern> [dir]}"
    local to="${2:?Usage: fo_rename <from_pattern> <to_pattern> [dir]}"
    local dir="${3:-.}"
    local dry="${4:-dry}"
    for f in $(fo_find "$from" "$dir"); do
        local new=$(basename "$f" | sed "s/$from/$to/")
        local target=$(dirname "$f")/"$new"
        if [ "$dry" = "dry" ]; then
            echo "WOULD: $f -> $target"
        else
            mv "$f" "$target"
            echo "MOVED: $f -> $target"
        fi
    done
}
