# Testing — Guide

## Manual Testing

```bash
# Quick test
./tau.py "hello"

# Chained inputs (human uses /fork CLI command, agent inside uses fork tool)
./tau.py "X=1" "/fork what is X"

# With specific LLM group
./tau.py --llm cuda "test prompt"
```

## Unit Tests

```bash
cd src && pytest          # Full suite
cd src && pytest test_agent_context.py  # Specific module
```

57 test files covering: context, LLM pipeline, tools, delegation, A2A, config, console, loop detection, models, file paths, tool validation, compression, edge cases, phantom detection, EOT recovery, vision recovery, loop escalation.

## End-to-End Tests: sanity.sh (GOLD STANDARD)

```bash
bash sanity.sh            # Full e2e suite (~100 seconds, requires LLM endpoint)
```

### sanity.sh — Absolute Prerequisite for Everything

`sanity.sh` is the **gold standard** and the **only gate** between broken code and production. It tests CLI, positional args, tool calling, fork functionality, continue command, and other critical paths.

**sanity.sh MUST pass 100% — zero failures, zero exceptions.**

### Absolute Rules

| Rule | Details |
|------|---------|
| **100% pass rate required** | Zero failures. Zero exceptions. No partial passes. |
| **No "pre-existing" excuses** | "Pre-existing error" or "not caused by current edits" is **NOT valid**. If it fails, fix it. |
| **Stop everything on failure** | If sanity.sh fails, STOP ALL OTHER WORK and fix the root cause. |
| **Never assume model failure** | Always investigate the code. Model failures are symptoms, not root causes. |
| **Never modify tests** | Tests, prompts, and expectations in sanity.sh are **immutable**. Fix the code, not the tests. |
| **Cannot proceed without 100%** | You cannot move forward on ANY task until sanity.sh passes 100%. |

### Why This Matters

sanity.sh is the only automated verification that the agent works end-to-end. A single failure means something fundamental is broken — whether it's a code regression, a configuration issue, or an environmental problem. Patching around failures or blaming the model compounds technical debt and erodes confidence in the codebase.

The correct response to **ANY** sanity.sh failure is:
1. Investigate the failure
2. Find the root cause in the code
3. Fix the code
4. Re-run sanity.sh until it passes 100%

### When sanity.sh Fails

```bash
# 1. Read the full log
cat $SANITY_LOG

# 2. Check agent log
cat $SANITY_AGENT_LOG

# 3. Reproduce the failing test manually
./tau.py "<failing prompt>"

# 4. Investigate the code path that caused the failure
# 5. Fix the root cause — never change the test
# 6. Re-run sanity.sh until it passes 100%
```

### Test Suite Skill

The `tau_testsuite` skill documents:
- Fast A2A testing (batch tests against single agent instance)
- Test structure and naming conventions
- Helper functions (`expect_*`, `log_*`, `create_test_file`, `run_tool_capture`)
- Test case organization by group (tc_1.* through tc_10.*)

See `skills/tau_testsuite/SKILL.md` for full test suite documentation.

## Testing Rules

| Rule | Details |
|------|---------|
| Gold standard | `sanity.sh` — end-to-end tests requiring LLM endpoint (~100 sec) |
| Unit tests | `cd src && pytest` — 57 test files covering core modules |
| Naming | `tc_<major>.<minor>.<idx>_<name>.sh` (e.g., `tc_1.0.1_basic.sh`) |
| Structure | SETUP → EXECUTE → VALIDATE → CLEANUP |
| Helpers | `expect_*()` functions — print PASS/FAIL, return 0/1 — **DO NOT INVERT** |
| Fast tests | `tc_10.*` group — batch A2A tests against single agent instance |
| Prompts | **NEVER modify `sanity.sh` prompts** — deliberately crafted |
