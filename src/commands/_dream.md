---
description: [DEPRECATED] Tau dreaming — use dream.py instead
---

# [DEPRECATED] Dream Orchestrator

**This command is DEPRECATED. Use `dream.py` instead.**

`dream.py` is the programmatic orchestrator for Tau self-improvement. It handles
all deterministic operations (file ops, git, testing, timeout, logging) and
invokes `tau.py` only for LLM-driven work.

## Why Deprecated
- This command required tau to manually run `./tau.py` in background
- `dream.py` provides explicit code for deterministic operations
- `dream.py` has proper timeout handling, logging, and single-instance lock
- `dream.py` is the canonical way to run the dream cycle

## How to Use Dream Now
```bash
python3 dream.py              # Forever (default)
python3 dream.py --n 3        # Limited cycles
python3 dream.py --llm deepseek
python3 dream.py --dry-run    # No LLM calls
```

See `skill('dream')` for complete documentation.

## Legacy Content (for reference only)

The original dream command did the following:
1. Enabled heartbeat (180 seconds)
2. Ran tasks from `../tasks/1_todo/` via the `/_taudotask` command
3. Ran 3x re-architecture via the `/_taurearch` command
4. Ran test commands via the `/_tautestcommands` command
5. Ran sanity tests via the `/_tautestsanity` command
6. Ran skill maintenance via the `/_tauskillmaintenance` command
7. Ran doc sync via the `/_taudoc` command
8. Ran log review via the `/_taulogreview` command
9. Between steps, reviewed changes and committed to git
10. Repeated the cycle endlessly

This is now handled by `dream.py` with proper error handling, timeouts, and logging.