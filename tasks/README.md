# Task Automation Harness

Automated task processing system for agent-driven code development.

## Overview

This harness automates the complete lifecycle of task implementation:
- **Plan**: Agent analyzes requirements and creates implementation plan
- **Implement**: Agent implements the plan step by step
- **Test**: Agent reviews implementation status
- **Testsuite**: Full test suite execution (formal qualification)
- **Commit**: Changes committed to git
- **Done**: Task moved to done folder and committed to git

## Philosophy

### Core Principles

**1. Atomic Operations**
- Every task result is a git commit (PASS or FAIL)
- No partial states, no checkpoints to restore
- Git commit = final truth

**2. Physical File Movement**
- Tasks move between directories, not just marked
- `mv todo → done` or `mv todo → failed`
- Directory state = task state

**3. Dual Logging**
- Main log (`automation.log`): Always receives all entries
- Workspace log: Same entries, created when workspace exists
- No switching, no loss of context

**4. Clean Separation**
- Phase 3 (agent review) ≠ Phase 4 (formal testsuite)
- Agent gets multiple cycles to fix (Phase 3)
- External runner is final gate (Phase 4)

**5. Error-First Design**
- Check before acting
- Rollback on failure
- Never leave system inconsistent

**6. Deterministic Behavior**
- Max 10 cycles per task
- 60s timeout for git operations
- 3600s timeout for agent phases
- Predictable outcomes

### Key Lessons Learned

1. **File Movement is Essential**: Touch files don't prevent reprocessing. Only actual file movement works.
2. **Git Commits > File Checkpoints**: Atomic, versioned, auditable. No file-based state to corrupt.
3. **Error Handling Must Be Explicit**: Silent failures hide problems. Fail fast, fail loud.
4. **Logging Context Matters**: Phase names, indentation, dual logging all improve debugging.
5. **Separation of Concerns**: Phase 3 (agent) ≠ Phase 4 (external). Clear boundaries prevent confusion.
6. **Documentation Must Match Code**: Outdated docs cause confusion. Keep them synchronized.
7. **Simplicity Wins**: Remove complexity. Git is enough.
8. **Idempotency**: Check file existence before moves. Handle already-moved files gracefully.

## Directory Structure

```
tasks/
├── todo/           # Pending tasks (TASK_##.md files)
├── done/           # Completed tasks (actual task.md files moved here)
├── failed/         # Failed tasks (actual task.md files moved here)
├── workspace/      # Task workspace folders (created per-task)
│   └── TASK_01/    # Workspace for TASK_01.md
│       ├── PLAN.md          # Implementation plan
│       ├── automation.log   # Phase-by-phase logs (dual logging: main + workspace)
│       ├── tool.log         # Agent tool logs
│       ├── audit.log        # Agent audit logs
│       └── test_output/     # Test suite outputs
│           └── testsuite.log
├── automate.sh     # Main automation controller
├── queue.sh        # Add new tasks to queue
└── README.md       # This file
```

## Quick Start

### Add a Task

```bash
./queue.sh "Implement feature X"
```

Creates `todo/TASK_##.md` with the next available number.

### Run Automation

```bash
# Process all pending tasks (continuous loop)
./automate.sh

# Process single task
./automate.sh todo/TASK_01.md
```

## Automation Flow

### Phase 1: PLAN
- Agent reads task from `todo/TASK_##.md`
- Analyzes codebase
- Writes `workspace/TASK_##/PLAN.md` with implementation plan and success criteria
- **On failure**: Continue to next cycle (agent retries)
- **Timeout**: 3600s (1 hour) per phase

### Phase 2: IMPLEMENT
- Agent reads PLAN.md and TASK file
- Implements changes in code directory
- Appends learnings to PLAN.md
- Iterates as needed
- **On failure**: Continue to next cycle (agent retries)
- **Timeout**: 3600s (1 hour) per phase

### Phase 3: TEST (Agent Review)
- Agent reviews implementation status
- Agent runs testsuite skill internally
- Agent attempts to fix any failures
- Agent validates 100% pass before proceeding
- **On failure**: Continue to next cycle (agent retries)
- **Timeout**: 3600s (1 hour) per phase

### Phase 4: TESTSUITE (Formal Qualification)
- External test runner validates all tests
- Mandatory pass required for task completion
- This is the final gate before task completion
- **On failure**: Break loop, go to FAIL cleanup

### Phase 5: PASS/FAIL Decision

**Exit Paths:**
- **SUCCESS**: Early return after PASS commit
- **FAIL**: Single cleanup at end of loop (revert, move to failed/, commit)

**5PASS Path:**
1. Move task file from `todo/` to `done/`
2. Git add the moved file
3. Git commit with message "AUTOMATE: TASK_01.md - PASS"
4. Task is complete (early return)

**5FAIL Path (Single Cleanup):**
1. Move task file from `todo/` to `failed/`
2. Git add . (all changes from repo root, captures task move)
3. Git commit with message "AUTOMATE: TASK_01.md - FAIL"
4. Task is marked as failed (user intervention required)

**When FAIL cleanup runs:**
- Phase 4 testsuite fails
- Max iterations (10) reached
- Git commit fails (rollback to todo/)

## Git Commit Strategy

### Initial Checkpoint
- One commit created at automation startup
- Includes ALL changes in the repository at that moment
- Serves as the rollback point for failed tasks
- **NOTE**: Ensure repository is clean (no uncommitted changes, no untracked files) before running automate.sh for predictable behavior

### Task Commits
- **PASS**: Commits task file move to done/ + any code changes
- **FAIL**: Commits task file move to failed/ + keeps code changes (no revert)
- Only known good states are committed to main branch
- FAIL commits capture the final state before failure

### Git Operations (Internal Implementation)

The automation uses two centralized git operations:

**`git_checkpoint(message)`** - Commits all changes:
- Goes to repository root
- Uses `git add .` to capture ALL changes from repo root
- Commits with given message
- On failure, does `git reset --hard HEAD` to rollback

**`git_rollback()`** - Rolls back to last checkpoint:
- Goes to repository root
- Does `git reset --hard HEAD` to undo all uncommitted changes
- Restores to last checkpoint state

### Rollback on Failure
- Uses `git_rollback()` - undoes all uncommitted changes
- Returns to last checkpoint state
- On commit failure, moves task back to `todo/` for retry

**Why this matters**: Old implementation used `git checkout -- .` which would restore files from the last commit, undoing our shell `mv` operations. New implementation uses `git add .` from repo root which correctly tracks file movements (deletion from old location, addition to new location).

## Looping Logic

- Continuous loop until no tasks in `todo/` directory
- Processes one task at a time
- Waits for new tasks if `todo/` is empty
- Task files are physically moved (not just touched)
- Tasks in `done/` or `failed/` are automatically skipped
- Each task has max 10 cycles before marking as FAIL

### Cycle Behavior

**Phase 1 (PLAN) failure**: Continue to next cycle (agent retries planning)
**Phase 2 (IMPLEMENT) failure**: Continue to next cycle (agent retries implementation)
**Phase 3 (TEST) failure**: Continue to next cycle (agent retries testing)
**Phase 4 (TESTSUITE) failure**: Break loop → FAIL cleanup
**Max iterations reached**: Break loop → FAIL cleanup

**Key insight**: Phases 1-3 allow agent iteration. Only Phase 4 is the definitive FAIL gate.

## Logging

- **Main log**: `tasks/automation.log` - always receives all log entries
- **Workspace log**: `workspace/TASK_##/automation.log` - receives same entries when in workspace (starts after Phase 1)
- Format: `[timestamp] [indent] [cycle] [phase] message`
- Indentation: 2 spaces for task start, +1 space for cycle start

## Safety Features

- **Git Checkpoint**: Initial commit provides rollback point
- **File Movement**: Tasks physically moved (not just marked)
- **Centralized Git Operations**: Two functions (`git_checkpoint`, `git_rollback`) ensure correct git behavior
- **Repository-Root Git Add**: `git add .` from repo root captures all changes including file movements
- **Error Handling**: Rollback on git commit failure
- **Existence Checks**: Only moves files if they exist in source directory
- **Timeout Protection**: 60s timeout for git operations, 3600s for agent phases
- **Max Iterations**: 10 cycles per task before marking as FAIL
- **Proper Error Reporting**: Explicit error messages, no silent failures
- **Workspace Preservation**: All iteration artifacts preserved for later analysis (no automatic cleanup)

## Task Recovery

### Failed Tasks
- Tasks in `failed/` can be manually retried
- User can move task back to `todo/` directory
- User should update task file before retrying
- Example: `mv failed/TASK_01.md todo/TASK_01.md`
- Workspace artifacts remain for debugging

### Completed Tasks
- Tasks in `done/` are preserved
- Original task.md file contains full history
- Workspace artifacts remain for reference
- No automatic cleanup (user can remove manually)

## Configuration

Environment variables:
- `AGENT`: Agent command (default: `tcuda`)
- `TIMEOUT`: Agent timeout per phase in seconds (default: `3600`)

## .gitignore

The `tasks/.gitignore` file ignores:
- `workspace/**` - all workspace directories
- `automation.log` - main log file

This file is committed to git for consistency across all deployments.

## Troubleshooting

### Task Stuck in Loop
- Check `workspace/TASK_##/automation.log` for phase failures
- Review `PLAN.md` for implementation issues
- Check test outputs in `workspace/TASK_##/test_output/`
- Verify task file is actually moving between directories (not just touching)

### Git Rollback Failed
- Verify code directory is valid git repository
- Check for uncommitted changes before running
- Ensure at least one initial commit exists
- Ensure .gitignore is committed to git

**Note**: The automation uses `git add .` from repository root to capture all changes including file movements. This replaces the older approach of using `git checkout -- .` which would restore files from the last commit, undoing our shell `mv` operations.

### Agent Timeout
- Increase `TIMEOUT` environment variable
- Check agent binary is accessible and working
- Review agent logs in `workspace/TASK_##/tool.log`

### Errors in Logs
- Look for explicit error messages (no silent failures)
- Check git add/commit commands for failures
- Verify task file exists before moves
- Review rollback logic if commit fails

## Architecture

### Components
- **automate.sh**: Main controller, 5-phase workflow (PLAN, IMPLEMENT, TEST, TESTSUITE, PASS/FAIL)
- **queue.sh**: Task queue manager
- **workspace/**: Per-task isolated workspaces
- **test/**: Test suite runner
- **git**: Atomic commits as checkpoints

### Design Principles
- **Atomicity**: Every result is a git commit
- **Isolation**: Each task has own workspace, no file sharing
- **Safety**: Git checkpoints protect against failures
- **Traceability**: Complete logs in each workspace + main log
- **Persistence**: All artifacts preserved for review
- **Simplicity**: Git commits replace complex checkpoint system
- **Idempotency**: Check file existence before operations
- **Two Exit Paths**: SUCCESS (early return) or FAIL (single cleanup)

## Migration Notes

### From Old System to New System

**Before (Broken):**
- Task files stayed in `todo/` forever
- Only `touch` files created in `done/` and `failed/`
- Infinite loops on same task
- Checkpoint file system (complex, error-prone)
- Phase 6 DONE with diff.patch creation

**After (Fixed):**
- Task files physically move between directories
- Git commits as checkpoints (simple, reliable)
- No infinite loops
- Proper error handling with rollback
- 5-phase workflow (PLAN, IMPLEMENT, TEST, TESTSUITE, PASS/FAIL)
- Two clear exit paths: SUCCESS (early return) or FAIL (single cleanup)
- Phases 1-3 allow agent iteration, Phase 4 is final gate

**Migration Steps:**
1. Ensure .gitignore is committed to git
2. Ensure code/ directory is clean before running
3. Run automation - it will create initial checkpoint commit
4. Tasks will move between directories automatically
5. Failed tasks can be manually retried by moving back to `todo/`

## Agent Integration

### Related Commands

- `/delegate <task>` — Enter orchestration mode; agent plans and delegates via fork/subagent. Use this to drive the task lifecycle from within the agent.
- `/plan <action>` — Manage hierarchical task plans (create, add, complete, block, status, next, progress, update, delete, clear). Use during PLAN phase to structure work.
- `/ralph <task>` — Iterative task execution with explicit confirmation. Use for complex tasks requiring multiple fork cycles.

### Related Skills

- `tau_testsuite` (`src/skills/tau_testsuite.md`) — Fast A2A testing, structured testcases, helpers. Use during TEST phase for validation.
- `code-simplifier` (`src/skills/code-simplifier.md`) — Simplify and refine code after IMPLEMENT phase.
- `review` (`src/skills/review.md`) — Code review process for pre-commit validation.

### How Agents Use This System

When working within the task harness, agents should:

1. **Read the task file** from `todo/TASK_##.md` to understand requirements
2. **Create a plan** in `workspace/TASK_##/PLAN.md` with success criteria
3. **Implement changes** in the code directory, iterating as needed
4. **Self-test** using the `tau_testsuite` skill before formal qualification
5. **Validate** all tests pass before marking task as complete

Agents can be invoked directly from `automate.sh` via the `AGENT` environment variable (default: `tcuda`). Each phase has a 3600s timeout.

---

## License

Internal use only.
