#!/bin/bash
# plan_helpers.sh — Quick plan file operations
# Usage: source skills/plan_template/plan_helpers.sh

set -euo pipefail

# Find in-progress tasks
plan_progress() {
    local file="${1:-PLAN.md}"
    grep -n "\[>\]" "$file" 2>/dev/null || echo "No in-progress tasks"
}

# Find pending tasks
plan_pending() {
    local file="${1:-PLAN.md}"
    grep -n "\[ \]" "$file" 2>/dev/null || echo "No pending tasks"
}

# Find completed tasks
plan_done() {
    local file="${1:-PLAN.md}"
    grep -n "\[x\]" "$file" 2>/dev/null || echo "No completed tasks"
}

# Find blocked tasks
plan_blocked() {
    local file="${1:-PLAN.md}"
    grep -n "\[?\]" "$file" 2>/dev/null || echo "No blocked tasks"
}

# Count tasks by status
plan_stats() {
    local file="${1:-PLAN.md}"
    local total=$(grep -c "\[.\]" "$file" 2>/dev/null || echo 0)
    local done=$(grep -c "\[x\]" "$file" 2>/dev/null || echo 0)
    local progress=$(grep -c "\[>\]" "$file" 2>/dev/null || echo 0)
    local pending=$(grep -c "\[ \]" "$file" 2>/dev/null || echo 0)
    local blocked=$(grep -c "\[?\]" "$file" 2>/dev/null || echo 0)
    echo "Total: $total | Done: $done | In Progress: $progress | Pending: $pending | Blocked: $blocked"
    if [ "$total" -gt 0 ]; then
        echo "Completion: $((done * 100 / total))%"
    fi
}

# Create a new plan file
plan_new() {
    local file="${1:-PLAN.md}"
    cat > "$file" << 'EOF'
# Task Documentation
## Original Request
[Describe the task]

## Recent Updates
[Track updates here]

# Plan
## Phase 1: [Name]
- [ ] Task 1
- [ ] Task 2

## Phase 2: [Name]
- [ ] Task 1
- [ ] Task 2

# Requirements
- **Purpose**: [What]
- **Inputs**: [From where]
- **Outputs**: [To where]

# Decisions
- [Decision]: [Rationale]

# Tasks
1. [Step] — [Tool] — [Expected] — [Verify]

# Questions
- [Open question]

# Risks
- [Risk]: [Probability] [Impact] [Mitigation]
EOF
    echo "Created $file"
}
