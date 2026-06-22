#!/bin/bash
set -euo pipefail

# QUEUE TASK - Add new task to automation queue
# Usage: $HOME/tau/tasks/queue.sh "task description"
# Can be run from any directory (self-aware)
# Creates TASK_##.md files in 1_todo/ directory

_SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
_TODO_DIR="${_SCRIPT_DIR}/1_todo"

mkdir -p "$_TODO_DIR"

# Find next sequence number by checking all directories
get_next_number() {
    local max=0
    local all_dirs="$_TODO_DIR ${_SCRIPT_DIR}/3_done ${_SCRIPT_DIR}/3_failed"
    
    for dir in $all_dirs; do
        [ -d "$dir" ] || continue
        for f in "$dir"/*; do
            [ -f "$f" ] || continue
            local basename
            basename=$(basename "$f")
            
            # Extract number from TASK_##.md pattern
            if [[ "$basename" =~ ^TASK_([0-9]+)\.md$ ]]; then
                local num="${BASH_REMATCH[1]}"
                if [ "$num" -gt "$max" ]; then
                    max="$num"
                fi
            fi
        done
    done
    
    echo $((max + 1))
}

next_num=$(get_next_number)
task_file="${_TODO_DIR}/TASK_$(printf '%02d' $next_num).md"

# Write task file
cat > "$task_file" << EOF
TASK: $*
EOF

echo "Created: $task_file"
