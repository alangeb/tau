# Changelog

## 2026-08-01 — Audit Logging Rework (v2)

### New Record Types
- Added 19 new audit record types: USER variants (manual/synthetic/source), ASSISTANT variants (response/reasoning), COMPRESS_RESULT, COMPRESS_END, CONTEXT_ADD, CONTEXT_REMOVE, CONTEXT_MERGE, CONTEXT_SNAPSHOT, CONSOLE_INFO, CONSOLE_SUCCESS, CONFIG_CHANGE, ERROR_RATE_ALERT, LOOP_DETECTION, LOOP_WARNING, SESSION_END
- Total record types: 36 (17 original + 19 v2)
- All record types use structured `[ISO_TIMESTAMP] RECORD_TYPE key=value nesting=N` format with `  | ` continuation lines

### Audit Writer API
- New v2 methods: `user_manual()`, `user_synthetic()`, `user_synthetic_fork()`, `user_synthetic_subagent()`, `assistant_response()`, `assistant_reasoning()`, `compress_result()`, `compress_end()`, `context_add()`, `context_remove()`, `context_merge()`, `context_snapshot()`, `console_info()`, `console_success()`, `config_change()`, `error_rate_alert()`, `loop_detection()`, `loop_warning()`
- Original methods preserved for backward compatibility

### Design Principles
- NEVER TRUNCATE: All content logged in full
- NEVER ROTATE: Audit file grows for session lifetime
- NEVER REVERT: Append-only, immutable records
- Audit is the source of truth for debugging and post-mortem analysis

### Tasks Completed
- AUDIT00: Discovery — complete inventory of audit system references
- AUDIT01: Documentation — updated design docs
- AUDIT02: Implementation — new record types and API methods
- AUDIT03: Review — code review and testing
- AUDIT04: Documentation review — verify consistency
- AUDIT05: Tool migration — migrate callers to v2 API
- AUDIT06: Cleanup — merge scratch files, final verification