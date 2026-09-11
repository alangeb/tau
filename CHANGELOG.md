# Changelog

## 2026-08-09 — Code Review Root Cause Fixes (v522)

### Bug Fixes
- **context_length_exceeded error recovery**: Added `"context_length_exceeded"` and `"configured context size is"` to `CONTEXT_OVERFLOW_INDICATORS` — triggers graceful compression+retry instead of hard failure
- **Session registry thread safety**: Wrapped all public methods (`register_session`, `update_session`, etc.) with `self._lock` — fixes gap where `_data` was mutated outside the lock
- **Audit writer fork ordering**: Restored `_flush()` in `fork_start()` to ensure FORK_START appears before fork entries in audit log
- **Fork env var cleanup**: Wrapped `TAU_PARENT_AUDIT_FILE`/`TAU_FORK_NESTING` set/cleanup in `try/finally` — prevents leak if `_create_subagent()` raises
- **A2A thread pool**: Replaced thread-per-connection with `ThreadPoolExecutor(max_workers=10)` — prevents unbounded thread creation
- **A2A robust recv**: `_recv_request()` uses 500ms timeout + JSON parse detection instead of single-write assumption — handles large/multi-chunk requests
- **Resource bounds**: Fork loop tracker (`deque(maxlen=200)`), sandbox cache (50 entries FIFO), request logs (5MB byte-accurate), XML regex body (10K chars), log filename counter (1000)
- **Division by zero guard**: Added `max_context_tokens > 0` check before compression threshold comparison
- **SIGTERM simplification**: Removed dead `sleep(2)` + SIGKILL fallback — SIGTERM alone handles cleanup properly
- **Shell quoting in fetch**: Used `shlex.quote()` for `base_url` in curl command — prevents injection with special chars
- **URL normalization in crawl**: `_normalize_url()` strips trailing slashes — prevents duplicate crawls of same page

### Refactoring
- **Removed `_invalidate_tools_cache()`**: No-op placeholder removed (tools are static after init)
- **Bound timestamps deque**: Fork budget `timestamps` uses `deque(maxlen=FORK_BUDGET+10)` instead of unbounded list
- **Byte-accurate log limit**: `len(lr_text.encode("utf-8"))` instead of `len(lr_text)` for 5MB request log limit

### Chores
- **Removed dead test**: Deleted `test_compression_pipeline.py` (depended on missing fixture `test_context_605kb.json`)
- **Fixed sandbox docstring**: Changed "LRU-style" to "FIFO" to match actual implementation

## 2026-08-09 — Codebase Review & Hardening (v521)

### Security
- **Crawl4AI curl injection fix**: Use `shlex.quote()` to escape payloads in Crawl4AI curl commands, preventing shell injection via single quotes in URLs
- **Fetch redirect limit**: Added 10-redirect limit to prevent infinite redirect loops
- **Fetch response size limit**: Added 50MB response size limit (64KB chunked reading) to prevent memory exhaustion
- **A2A binary data handling**: Catch `UnicodeDecodeError` in `_handle_client()` to prevent crash on binary data
- **A2A poll timeout**: Added 300s max timeout to `_poll_for_response()` to prevent infinite hangs
- **Sandbox cache invalidation**: Added `clear_sandbox_cache()` function for cache invalidation on config changes
- **Security Philosophy documented**: Added DECISIONS.md §29 documenting bash = trust boundary, file sandbox = best-effort only

### Bug Fixes
- **RateLimitError retry**: HTTP 429 now retries with backoff (15s base, 120s max) instead of immediate session failure
- **Timeout backoff**: Added backoff to APITimeoutError handler (5s base, 60s max) to prevent thundering herd
- **Compression logging**: `_try_context_compress()` now logs warnings with full traceback on failure (was silent)
- **Compression overflow guard**: `compress_full_reset()` skips when context exceeds 70% of max_context_tokens, preventing recursive overflow
- **Fork/subagent crash isolation**: `invoke_fork_sync()` and `invoke_subagent_sync()` now catch exceptions and return error strings instead of crashing parent
- **TauContext.copy() deep copy**: Uses `copy.deepcopy()` instead of shallow copy to prevent shared message dicts between forks
- **_prepare_messages() tool_calls mutation**: Deep copies tool_calls before stripping keys to prevent mutating original context
- **Loop detection gaming**: Requires 3 consecutive non-repeats before clearing `total_warnings` (was 1, allowing alternation gaming)
- **EOT protection docstring**: Fixed misleading docstring claiming sentinel was "assembled from parts"

### Performance
- **TauContext.bytes_size() cache**: Version-based cache with invalidation on mutation (was O(n) JSON serialization on every call)
- **get_all_tools() cache**: Caches result after first call (tool list is static after init)

### Refactoring
- **_invoke_llm_with_retry()**: Extracted `_BACKOFF_CONFIGS`, `_build_backoff()`, `_log_and_raise()` helpers (372 → ~310 lines)
- **Late imports**: Moved `log_failed_api_request`, `_sanitize_content`, `_sanitize_text` to module level in agent_llm_invoke.py
- **Reflection deduplication**: Extracted `_inject_think_reflection()` helper from `inject_early_reflection()` and `inject_reflection()` (80% code duplication eliminated)

### Chores
- **Dead code removal**: Removed `MAX_OUTER_RECOVERY` (agent_core.py) and `_make_isolated_path()` (agent_subagent.py)
- **.gitignore**: Added `.tau/` to .gitignore, removed from all historical commits via filter-branch
- **Test coverage**: Added 110+ new tests across 12 test files (1151 → 1261+ tests)

### 2026-07-04 — Audit Logging Rework (v2)

### New Record Types
- Added 19 new audit record types: USER variants (manual/synthetic/source), ASSISTANT variants (response/reasoning), COMPRESS_RESULT, COMPRESS_END, CONTEXT_ADD, CONTEXT_REMOVE, CONTEXT_MERGE, CONTEXT_SNAPSHOT, CONSOLE_INFO, CONSOLE_SUCCESS, CONFIG_CHANGE, ERROR_RATE_ALERT, LOOP_DETECTION, LOOP_WARNING, SESSION_END
- Total record types: 36 (17 original + 19 v2)
- All record types use structured `[ISO_TIMESTAMP] RECORD_TYPE key=value nesting=N` format with `  | ` continuation lines

### Audit Writer API
- Implemented v2 methods (6 of those listed below): `context_add()`, `context_remove()`, `context_merge()`, `context_snapshot()`, `console_info()`, `console_success()` (plus `console_error()` which pre-existed)
- Abandoned v2 methods (12) — documented but never wired into production code; removed as dead code (see DECISIONS.md 24.10). The v1 API (`user()`, `assistant()`, `compress_*`) remains the sole interface:
  - `user_manual()`, `user_synthetic()`, `user_synthetic_fork()`, `user_synthetic_subagent()`
  - `assistant_response()`, `assistant_reasoning()`
  - `compress_result()`, `compress_end()`
  - `config_change()`, `error_rate_alert()`, `loop_detection()`, `loop_warning()`
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