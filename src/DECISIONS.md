# Design Decisions

## Architecture (8)

| # | Decision | Rationale |
|---|----------|-----------|
| 1.1 | **Central `TauErgon` orchestrator** — one class owns context, LLM, tools, loop detection, subagents | Single ownership, clear responsibility |
| 1.2 | **Message-driven architecture** — user input → context → LLM → tools → repeat | Simple, composable flow |
| 1.3 | **Single entry point** (`tau.py`) with identical `tau-dut.py` for testing | Clean separation of production and test variants |
| 1.4 | **System prompt from `AGENT.md`** — externalized, not hardcoded | Configurable behavior without code changes |
| 1.5 | **`AgentInitConfig`** — fully-resolved initialization parameters in `agent_init.py` via `resolve_agent_init()`; separates config resolution from agent construction | Clean init pipeline |
| 1.6 | **`CommandManager`** — unified command resolution and dispatch in `agent_commands.py`; resolves `.py` → builtin → `.md` priority with `CommandSource`/`CommandInfo` | Centralized command routing |
| 1.7 | **`InputHandler`** — manages stdin thread, signal handling, and input dispatch in `agent_input.py`; separates input loop from agent core | Decoupled input processing |
| 1.8 | **`agent_subsystems.py`** — `SubsystemBundle`, `init_subsystems()`, `read_system_prompt()` encapsulate subsystem creation and wiring; reduces import burden on `agent_core.py`; makes subsystem init testable in isolation | Separation of concerns, testability |

## Compression (18)

| # | Decision | Rationale |
|---|----------|-----------|
| 2.1 | **Eleven sequential algorithms**: prune_images → oversized_tool_redaction → drop_reasoning → last_transaction → tool_pruning → redact_blocks → tool_pruning_full → redact_blocks_full → full_reset → conversation_summary → blind_truncate | Ordered by impact: image pruning first, then structural redaction, then LLM summary of recent turns, then boundary-limited pruning/redaction, then full-context pruning/redaction, full reset, then deterministic conversation summary, then blind truncation as absolute last resort |
| 2.2 | **Fixed 50% byte boundary** — computed ONCE from original context, never moves during compression | Predictable, preserves recent context |
| 2.3 | **Right-to-left scanning** — compresses oldest blocks first to preserve KV cache prefix | KV cache efficiency |
| 2.4 | **Parameter consistency across LLM calls** — same model/tools/tool_choice/params; only `messages` varies → enables full KV cache reuse | Maximize cache hits |
| 2.5 | **Compression prompt is a constant string** — never changes between calls → prefix stability | KV cache prefix stability |
| 2.6 | **Tool pruning threshold: 100 bytes** — smaller outputs not worth pruning overhead | Cost-benefit tradeoff |
| 2.7 | **Minimum block size: 300 bytes** — avoid LLM call overhead on tiny blocks | Efficiency threshold |
| 2.8 | **Retry on short LLM responses (<10 bytes)** — compression summaries must be substantive | Quality gate |
| 2.9 | **Preserve `tool_call_id` and `name` when pruning** — maintains OpenAI spec compliance | API compatibility |
| 2.10 | **`compress_oversized_tool_redaction` as first algorithm** — strips oversized tool outputs (>20% of context) before other compression | Targets disproportionately large outputs first |
| 2.11 | **Two-tier boundary strategy** — steps 4–5 respect 50% boundary; steps 6–7 scan entire context | Graduated escalation: protect recent context first, then compress everything if needed |
| 2.12 | **`compress_drop_reasoning` as second algorithm** — strips reasoning fields before LLM summarization | Cheap, high-yield reduction before expensive LLM calls |
| 2.13 | **`compress_prune_images` as first algorithm** — replaces image blocks with text placeholders (keeps last image per message); images dominate context size; right-to-left within 50% boundary | Most aggressive reduction: images are the largest context consumers |
| 2.14 | **`compress_conversation_summary` as tenth algorithm** — deterministic restructuring (no LLM call) that condenses entire conversation into a single summary user message; preserves ALL interaction history in compact structured format; always OpenAI-alternation-compliant | Guaranteed compression when all LLM-based methods fail; zero API cost; preserves complete interaction history |
| 2.15 | **`compress_blind_truncate` as eleventh algorithm** — last-resort truncation of summary message from the beginning; guaranteed to produce context within target_size_bytes; preserves most recent information | Absolute fallback: when even deterministic summary is too large, truncate from oldest end |
| 2.16 | **Dynamic compression threshold based on loop escalation** — `compress_threshold` starts at 0.85 (normal), drops to 0.65 at escalation_level 1, drops to 0.35 at escalation_level 2+ | When the loop is stuck, breaking it takes priority over preserving KV cache; aggressive compression before the LLM call prevents the model from operating on bloated context |
| 2.17 | **Compression runs both before AND after LLM call** — pre-call compression (line ~106) uses dynamic threshold based on escalation; post-call compression (line ~193) uses static 0.85 threshold as safety net for context growth during LLM call | Two-stage defense: pre-call prevents LLM from seeing bloated context, post-call catches growth that happens during the LLM call itself |
| 2.18 | **Pre-call compression location: after context validation, before LLM call** — ensures context is valid before compressing, and LLM always sees a clean context | Safety: validate first, compress second, then call LLM |

## LLM Layer (18)

| # | Decision | Rationale |
|---|----------|-----------|
| 3.1 | **`SimpleOpenAIClient` — stdlib-only HTTP client** — no external dependencies for LLM communication | Zero-dependency core |
| 3.2 | **Drop-in OpenAI client interface** — wraps raw API to match OpenAI SDK semantics | Familiar interface, easy migration |
| 3.3 | **Unified retry logic** — `_invoke_llm_with_retry` handles all retries, backoff, validation | Centralized error handling |
| 3.4 | **Post-parse recovery** — extract tool calls from text content when LLM misses structured format | Robustness against LLM quirks |
| 3.5 | **Validate before sending to API** — check tool call JSON, empty replies, length limits | Fail fast, save API calls |
| 3.6 | **`InvalidReplyError` for retryable violations** — fast-fail on first error | Clear error signaling |
| 3.7 | **XML-style and pipe-style tag constants** — centralized in `agent_llm_tool_parse.py` | Single source of truth |
| 3.8 | **`CacheTracker` with sliding window** — tracks prompt cache hit rates across session | Observability |
| 3.9 | **End-of-turn validation** — check for unclosed thinking tags, malformed tool-call syntax | Quality gate |
| 3.10 | **Pre-API field stripping** — remove non-LLM-relevant fields to avoid 400 errors | Defensive coding |
| 3.11 | **Defensive parsing** — `_safe_get`, deep copies, external tracking sets | Robust against malformed responses |
| 3.12 | **Graduated retry strategy** — thinking disabled after 5 failures | Adaptive behavior |
| 3.13 | **Bounded logging** — prevent console flooding | UX protection |
| 3.14 | **Cross-backend support** — handles both vLLM and llama.cpp formats | Backend agnostic |
| 3.15 | **Conservative post-parse** — only extracts clearly valid tool calls | Safety over flexibility |
| 3.16 | **`PrefixCacheTracker` in `agent_llm_cache.py`** — tracks expected vs actual prefix cache hits, reports divergence with param change detection | Cache observability |
| 3.17 | **`LLMCallConfig` dataclass** — unified configuration for LLM invocations (model, messages, tools, tool_choice, stream, extra_kwargs) | Centralized call config |
| 3.18 | **In-place compression replaces truncation** — overflow recovery uses LLM-based compression on real context, eliminating redundant copy compression | Overflow tracking |

## Tooling (20)

| # | Decision | Rationale |
|---|----------|-----------|
| 4.1 | **Dynamic tool discovery** — scan `tools/` directory for modules with `name` + `run` attributes | No manual registration |
| 4.2 | **`ToolEntry` dataclass** — single source of truth for tool metadata | Clear structure |
| 4.3 | **`Args` dataclass per tool** — schema generated automatically via `_dataclass_to_json_schema` | Auto-schema, no manual maintenance |
| 4.4 | **`CMD_ALIASES` and `ARG_ALIASES`** — tool/argument aliasing for flexibility | LLM-friendly naming |
| 4.5 | **Signal-based tool execution** — `signal.setitimer()` with `SIGALRM` handler raises `ToolTimeout`; no daemon threads, no orphaned processes | Clean interruption, zero concurrency |
| 4.6 | **Tool validation: aliases first, then int coercion** — `normalize_tool_call` normalizes before execution | Flexible input handling |
| 4.7 | **Oversized output to `LOG_DIR`** — `write_oversized_output()` in `agent_session.py` stores full output on disk, context stays small | Disk backup, token economy |
| 4.8 | **Tool errors via `AuditWriter`** — structured audit records in `LOG_DIR`, accumulates per session | Machine-readable error history |
| 4.9 | **`ToolFilter`: allowlist > blocklist, `fnmatch` wildcards** — deny-by-instructive-message | Flexible restriction |
| 4.10 | **Priority timeout resolution**: args > module `timeout` attr > `default_timeout` (180s) > `long_running_timeout` (86400s for fork/subagent) | Fine-grained control |
| 4.11 | **Process group isolation** — `start_new_session=True` on all `subprocess.run()` calls in tool modules; each tool manages its own child process cleanup; no centralized ProcessTracker | Zero orphaned processes |
| 4.12 | **Sequential batch execution** — maintains OpenAI message alternation | API compliance |
| 4.13 | **No exceptions escaped** — all errors returned as strings | Predictable error handling |
| 4.14 | **`difflib` suggestions** for unknown tools (cutoff=0.6) | Helpful error messages |
| 4.15 | **Comprehensive exception catching** — 7 exception types | Robust tool execution |
| 4.16 | **Dangerous command detection** — `bash` tool blocks destructive patterns (`rm -rf`, `sudo`, `git --force`) via `DANGEROUS_PATTERNS`; rejected on first attempt, allowed on double-call confirmation | Safety gate |
| 4.17 | **Sandbox validation** — `tools/lib/sandbox.py` enforces working directory boundaries via `check_path`/`validate_path`; paths outside cwd require double-call confirmation | Escape prevention |
| 4.18 | **`ToolModule` protocol** — formal protocol in `tools/__init__.py` requiring `metadata` (ToolMetadata), `Args` (dataclass), `run` (callable); validated via `_validate_tool_module()` | Structured tool registration |
| 4.19 | **Tool validation module** — `tools/validation.py` provides `normalize_tool_call`, `validate_tool_name`, `_get_tool_schema_info`, `_validate_tool_args`, `_generate_validation_error` | Robust tool call normalization |
| 4.20 | **`wiki` tool** (`tools/wiki.py`) — manage wiki configuration: get/set wiki path in `tau.json` under `wiki.path`, check wiki status (exists, git status, file count, size); stored path persists across sessions | Wiki infrastructure management |

## Console & Communications (8)

| # | Decision | Rationale |
|---|----------|-----------|
| 5.1 | **Console output via standalone functions** — `agent_console/` package provides: primitives (low-level I/O: `_cw()`, `_role_color()`, `Colors`, `echo()`, `status()`, etc.), messages (display helpers: `display_error()`, `display_warning()`, `display_success()`, `display_info()` + `_ConsoleMessage` declarative templates + `MessageRegistry` + message definitions); no singleton class | Consistent formatting, no global state, focused modules |
| 5.2 | **Semantic color coding** — RED=error, YELLOW=warning, CYAN=status, GREEN=success, TEAL=reasoning | Visual clarity |
| 5.3 | **A2A via Unix domain sockets** — inter-agent communication protocol with JSON messages | Process-local, secure |
| 5.4 | **`InputMessage` factory pattern** — `from_a2a()`, `from_interactive()`, `from_command_line()` → unified input type | Source-agnostic processing |
| 5.5 | **Auto-timestamping via `__post_init__`** — all messages get timestamps automatically | Traceability |
| 5.6 | **Tool output truncation: 500 chars or 20 lines** (whichever hits first) — prevents console flooding | UX protection |
| 5.7 | **Dynamic `sys.stdout`** — supports output redirection | Testability |
| 5.8 | **Input prefix protocol** — `#`/`#!` start multiline blocks, `!` executes shell, `+` steers, `/` dispatches commands; inside blocks: `#+` routes steering, `#/` executes commands, 2+ blank lines submit | Flexible input modes with clear separation; prevents ambiguity between comments and commands |

## Subagent & Fork (11)

| # | Decision | Rationale |
|---|----------|-----------|
| 6.1 | **Subagent = blank slate** — fresh context, no parent history | Maximum isolation |
| 6.2 | **Fork = deep copy** — inherits full parent context + conversation | Context continuity |
| 6.3 | **Nesting depth threshold** — configurable limit on subagent/fork depth | Infinite recursion prevention |
| 6.4 | **Nesting restriction text injected into system prompt** — tells subagents their depth limit | Self-aware agents |
| 6.5 | **`_create_subagent` inherits parent config** — same LLM, same settings | Consistent behavior |
| 6.6 | **Unrestricted child tools by default** — children get full tool access unless filtered | Flexibility |
| 6.7 | **Fresh fork metadata** — not inherited from parent | Clean state |
| 6.8 | **`/fork {prompt} user message`** — signals fork context | Clear context markers |
| 6.9 | **Local imports** — avoids circular dependencies | Module independence |
| 6.10 | **Fork isolation via `_create_fork_isolation`** — each fork gets unique `fork_id` and isolated temp directory; cleaned up after completion | Resource isolation |
| 6.11 | **Forks are synchronous/blocking** — parent blocks until fork returns; no concurrent fork execution | Simplicity, predictable behavior |

## Delegate Mode (7)

| # | Decision | Rationale |
|---|----------|-----------|
| 7.1 | **Delegate mode via `/delegate` command** (`commands/delegate.py`) — ToolFilter enforces read-only behavior at execution time; all tools still announced (prefix cache preserved); orchestrator plans and delegates via fork/subagent | Safety + cache safety |
| 7.2 | **Delegate uses ToolFilter allowlist** — `_ALLOWED_DELEGATE_TOOLS` in `commands/delegate.py` restricts to read/analysis + delegation tools; non-allowed tools blocked with denied message; prefix cache preserved because tools are still announced | Execution-time enforcement |
| 7.3 | **ToolFilter changes in delegate mode** — `tool_filter` IS modified at runtime; this does NOT break prefix caching because `available_tool_names` (announced to LLM) is unchanged; filter only affects execution-time blocking | Prefix cache preservation |
| 7.4 | **`DELEGATE_INSTRUCTIONS` injected into context** — self-correcting behavior via prompt instructions | Enforced pattern |
| 7.5 | **`end_turn` as explicit loop terminator** — no hard iteration limit | Flexible orchestration |
| 7.6 | **Loop exit: check `invoke_with_tools()` return value** — loop only continues if result is `None` (interrupted); exits for any string response (normal or error) | Correct termination |
| 7.7 | **Max iteration limit (10)** — safety net to prevent infinite loops on continuous interrupts | Robustness |

## Input & Interaction (5)

| # | Decision | Rationale |
|---|----------|-----------|
| 8.1 | **Multiline input with `#` prefix** — two blank lines to end | Natural editing |
| 8.2 | **Two-level Ctrl+C** — graceful shutdown → force exit | User control |
| 8.3 | **Thread-safe everywhere** — `OutputCapture` with `threading.Lock`, `queue.Queue` for input | Concurrency safety |
| 8.4 | **System-wide flags** (`_interrupted`, `_exit_requested`) — cooperative cross-thread shutdown | Clean termination |
| 8.5 | **`InputHandler` stdin daemon thread** — reads stdin in background with `select()`; dispatches `/commands`, `!shell`, and regular input | Non-blocking input |

## Commands (15)

| # | Decision | Rationale |
|---|----------|-----------|
| 9.1 | **Three-tier dispatch: .py → builtin → .md** — Python commands override builtins, builtins override markdown | Flexible extension hierarchy |
| 9.2 | **Python commands: full agent access** — `run(agent, args)` with no return value, manages own context | Arbitrary program logic |
| 9.3 | **Markdown commands: prompt templates** — YAML frontmatter, placeholder substitution, multi-prompt chains | Easy authoring |
| 9.4 | **Dynamic placeholder substitution** — `${time}`, `${date}`, `${datetime}` resolved at load time | Flexible prompts |
| 9.5 | **Cached discovery** — `CommandRegistry` caches discovered commands; `clear_cache()` for invalidation | Performance with invalidation support |
| 9.6 | **Conflict resolution** — .py wins over .md for same name, with console warning | Predictable precedence |
| 9.7 | **Simple YAML parsing** — only `description:` field | Minimal complexity |
| 9.8 | **Relative default directory** (`commands/`) | Portable |
| 9.9 | **Three-category help display** — /help and /commands show builtins, .py, .md separately | Clear visibility |
| 9.10 | **`ralph` command** — iterative task execution with explicit `<complete>` tag confirmation; maintains task state in JSON files under `~/.local/tau/ralph/` | Structured task workflow |
| 9.11 | **`plan` command** — hierarchical task plan management (create, add, complete, block, unblock, status, next, progress, update, delete, clear) | Task organization |
| 9.12 | **`CommandSource` enum** — tracks origin (builtin, .py, .md) for each resolved command | Debugging & precedence |
| 9.13 | **`CommandManager.dispatch` recursion guard** — `MAX_MD_COMMAND_RECURSION` prevents infinite .md command chains | Safety against recursive prompts |
| 9.14 | **`health` command** (`commands/health.py`) — model server health monitoring dashboard with subcommands `status`, `reset`, `check`; displays `CircuitState` (closed/open/half_open), failure rate, consecutive failures/successes, recovery attempts, last error | Operational observability for LLM server health |
| 9.15 | **`_tautest` command** (`commands/_tautest.md`) — general testing orchestrator: runs `./tau.py` with parameters, creates test plans, fixes issues found; standalone command (not part of dream cycle) | General-purpose testing interface |

## Skills (5)

| # | Decision | Rationale |
|---|----------|-----------|
| 10.1 | **Skills loaded from `SKILLS_DIR`** — markdown files with category metadata | Easy authoring |
| 10.2 | **Cached skill list** — loaded once, cached after first call | Performance |
| 10.3 | **Fuzzy/case-insensitive skill matching** — flexible lookup | User-friendly |
| 10.4 | **Skill execution via fork** — inherits full context + skill content as instructions | Context-aware execution |
| 10.5 | **Shared skill discovery** (`lib/skill_discovery.py`) — `SkillInfo` TypedDict, `discover_skills()` supports both folder-per-skill (`skills/name/SKILL.md`) and legacy flat-file (`skills/name.md`) formats; deduplication with folder-per-skill winning; `skill_name_from_path()` is canonical name extraction used by `tools/skill.py` and `validate_skills.py` | Single source of truth for skill path resolution |

## Background Processes (TMUX) (3)

| # | Decision | Rationale |
|---|----------|-----------|
| 11.1 | **Session naming convention: `tmux-agent-{uuid}`** — auto-generated UUID, prefix for filtering | Unique identification |
| 11.2 | **Session lifecycle: new → exec → capture/tail → kill** — full lifecycle management | Complete control |
| 11.3 | **Kill all via prefix filter** — `tmux-agent-*` pattern for bulk cleanup | Efficient cleanup |

## Web Interaction (7)

| # | Decision | Rationale |
|---|----------|-----------|
| 12.1 | **Crawl4AI first-attempt with native fallback** — `fetch` tries Crawl4AI `/md` endpoint first, falls back to native HTML-to-markdown conversion | Flexible extraction |
| 12.2 | **SearXNG for searching** — `web_search` uses SearXNG for privacy-friendly search | Privacy |
| 12.3 | **Cache flag** — `cache=True` default in tool schema; Crawl4AI first-attempt uses `"c": "0"` to disable its cache; native fetch fallback uses local file cache with TTL | Fresh data by default |
| 12.4 | **Subagent/fork context recommended** — web fetching should be delegated for isolation; advisory only, not enforced | Isolation guidance |
| 12.5 | **Single URL → `/md` endpoint** (markdown), Multiple URLs → `/crawl` endpoint (JSON) | Optimized endpoints |
| 12.6 | **Filter types**: raw/fit/bm25/llm — configurable extraction strategies | Flexible extraction |
| 12.7 | **Multi-engine search** — `search` tool uses SearXNG → DuckDuckGo HTML → Mojeek cascade; `lookup` uses Wikipedia API + DuckDuckGo Instant Answer | Redundant search coverage |

## Loop Detection (7)

| # | Decision | Rationale |
|---|----------|-----------|
| 13.1 | **Dual-strategy**: consecutive repeat + Shannon entropy | Comprehensive detection |
| 13.2 | **Repeat threshold: 3** (configurable) | Sensitivity tuning |
| 13.3 | **Entropy threshold: 1.5 bits** (hardcoded in `agent_loop_detect.py`, not configurable via `LoopDetectionConfig`) | Diversity threshold |
| 13.4 | **Rolling window: 30 calls** (configurable, min 10 for entropy) | Context window |
| 13.5 | **Stats observability** via `get_stats()` | Monitoring |
| 13.6 | **Escalation levels** — `LoopDetector` tracks warning levels 1–4 with separate repeat and entropy templates; triggers `LoopEscalationManager` for reflection injection and recovery | Progressive intervention |
| 13.7 | **Sustained entropy detection** — `LoopDetector` tracks entropy over multiple rolling windows (`sustained_window=3`, `sustained_threshold=2.5`); triggers warnings when entropy stays consistently below threshold for N consecutive windows; catches 3-tool cycles (entropy ~1.585) that exceed the 1.5 instantaneous threshold; `sustained_warning_cooldown` parameter was added but never used (dead code) | Catches cycles above instantaneous threshold; avoids false positives from short bursts |

## A2A Protocol (15)

> **Protocol contract**: See [`A2A_PROTOCOL.md`](A2A_PROTOCOL.md) for the full v1.0 specification — message types, constants, client utilities, session discovery, server lifecycle, audit record types, CLI interface, and error handling.

| # | Decision | Rationale |
|---|----------|-----------|
| 14.1 | **JSON over Unix domain sockets** — all inter-agent messages are JSON-encoded, sent via `AF_UNIX` | Process-local, secure |
| 14.2 | **Socket naming: `/tmp/taua2a-{PID}.sock`** — each agent gets a unique socket path based on its PID | Collision-free |
| 14.3 | **Two request types: `agent_card` (sync) and `query` (async)** — metadata is immediate, queries are queued | Lightweight discovery |
| 14.4 | **Request ID correlation (UUID)** — every query gets a unique `id`, responses carry the same `id` | Response matching |
| 14.5 | **Acknowledgment pattern** — server sends `{"type": "queued"}` immediately, then `{"type": "response"}` later | Client confirmation |
| 14.6 | **Daemon thread for accept loop** — `_accept_loop` runs as `daemon=True` | Clean shutdown |
| 14.7 | **Per-client daemon threads** — each connection spawns its own thread | Concurrent clients |
| 14.8 | **`threading.Event` for startup synchronization** — `_ready` event set after bind/listen | Startup coordination |
| 14.9 | **Socket timeout of 1.0s in accept loop** — allows periodic checking of `self.running` flag | Graceful shutdown |
| 14.10 | **`SO_REUSEADDR` on server socket** — prevents "address already in use" on restart | Restart safety |
| 14.11 | **Scan `/tmp` with glob `taua2a-*.sock`** — filesystem-based discovery | Simple discovery |
| 14.12 | **Active-only default for `list_agents` display** — `_filter_active_agents` strips non-active by default | Clean output |
| 14.13 | **`json.JSONDecoder.raw_decode()` for streaming** — handles concatenated/fragmented JSON | Robust parsing |
| 14.14 | **A2A CLI mode** (`a2a_cli_mode`) — no agent created for discovery queries; short-circuits to direct socket communication for `--list`, `--card`, `--query` | Efficient discovery |
| 14.15 | **Heartbeat protocol** — server sends periodic heartbeats (`HEARTBEAT_INTERVAL=5s`) while polling for response; client uses idle-based timeout (`HEARTBEAT_IDLE_TIMEOUT=30s`) instead of wall-clock timeout; slow agents work indefinitely as long as heartbeats flow; dead server detected via missed heartbeat | Replaces fixed timeouts with adaptive liveness detection |

## Entry Point (7)

| # | Decision | Rationale |
|---|----------|-----------|
| 15.1 | **Identical `tau.py` and `tau-dut.py`** — two copies of the same entry point | Test isolation |
| 15.2 | **Line-buffered stdout** — `sys.stdout.reconfigure(line_buffering=True)` at module level | Interactive responsiveness |
| 15.3 | **Pre-parser for `--llm`** — resolves LLM group before building full parser | Correct help text |
| 15.4 | **`None` defaults for `--base-url`, `--model`, `--ctx`** — distinguish "user set" vs "group default" | Runtime switching |
| 15.5 | **`nargs="*"` for positional `inputs`** — zero or more inputs | Flexible invocation |
| 15.6 | **A2A client flags short-circuit to `a2a_cli_mode()`** — no agent created | Efficient discovery |
| 15.7 | **`--keep-alive` flag** — for A2A server mode | Headless operation |

## Think Tool (5)

| # | Decision | Rationale |
|---|----------|-----------|
| 16.1 | **Read-only fork** — `Think` spawns a fork with restricted tool access | Safe reasoning |
| 16.2 | **Allowlist of safe tools** — `glob`, `file_read`, `head`, `wc`, `pyscan`, `pyanalyze`, `grep`, `info`, `skill` | Read-only operations |
| 16.3 | **`THINK_PROMPT` constant** — pre-defined prompt for focused thinking | Consistent behavior |
| 16.4 | **No arguments required** — task is implicit in context | Simple interface |
| 16.5 | **`THINK_TOOL_ALLOWLIST` in `tools/think.py`** — explicit `frozenset` of allowed tools; `_build_safe_fallback` provides graceful degradation when fork fails | Safety + resilience |

## Cross-Cutting Principles (11)

| # | Decision | Rationale |
|---|----------|-----------|
| 17.1 | **`force_end_turn` mechanism** — any tool can terminate the current turn | Explicit control |
| 17.2 | **Graceful degradation** — features fail silently, agent continues operating | Resilience |
| 17.3 | **No external dependencies for core** — stdlib-only where possible | Zero-dependency core |
| 17.4 | **Heartbeat system** — idle detection with configurable interval | Self-monitoring |
| 17.5 | **`SubAgentResult` captures output + token metrics** — structured result containers | Observability |
| 17.6 | **Atomic single-append writes** — no explicit file locking | Concurrency safety |
| 17.7 | **Config source annotations** — `[env]`, `[file]` transparency in status display | Configuration visibility |
| 17.8 | **`ErrorRateTracker`** — thread-safe sliding window error rate tracking with burst detection and alert thresholds in `agent_audit_writer.py` | Proactive error monitoring |
| 17.9 | **`TokenTracker`** — centralized token accounting in `agent_token_tracker.py` with session-wide and per-turn counters; integrates `CacheTracker` for cache hit rates | Granular token observability |
| 17.10 | **NO angle brackets in Python source** — Python files MUST NOT contain literal ``, `=` characters; use `chr(60)`, `chr(62)`, `chr(60)+chr(61)`, `chr(62)+chr(61)` or variable composition (`LT = chr(60)`) instead | `file_write` tool strips XML-like tags from content, corrupting Python code with comparison operators |
| 17.11 | **XML argument stripping REMOVED** — `_sanitize_arg_value()` in `tools/validation.py` was a NO-OP and has been removed; XML regex constants were deleted; the regex `r']*>'` stripped ALL `` sequences including legitimate Python comparison operators (`=`, `< threshold`); cannot distinguish legitimate XML/HTML in tool args vs. leaked LLM tags; root cause was over-aggressive regex, not a language constraint | `file_write` tool's XML stripping was the symptom; the correct fix was removing the sanitizer entirely rather than banning angle brackets from source code |

## Context Management (18)

| # | Decision | Rationale |
|---|----------|-----------|
| 18.1 | **`TauContext._fork_metadata` separation** — fork metadata (pending tool calls, fork identity) stored separately from conversation history | Clean compression while preserving fork state |
| 18.2 | **Context validation after every mutation** (`_validate_on_mutation`) — enforces alternating USER/ASSISTANT turns, matching tool call/result pairs, no orphaned tool calls | API compliance |
| 18.3 | **`close_turn` mechanism** — ensures context ends in valid terminal state after incomplete turns | Graceful recovery |
| 18.4 | **`is_synthetic_message()` unified detection** — single function checks `SYNTHETIC_PREFIX` marker on any message (user or assistant); replaces old `_is_synthetic_user_message()`; **utilities moved to `agent_message_utils.py`** (zero-dependency module) | Eliminated redundant detection logic |
| 18.5 | **Synthetic message protocol** — all system-injected messages use `SYNTHETIC_PREFIX = "[SYSTEM-SYNTHETIC: "` marker; `make_synthetic_user(category, content)` factory creates them; recovery paths inject synthetic user messages (NOT tool calls) to maintain OpenAI alternation; `is_synthetic_message()` detects them; `get_last_real_user_prompt()` finds real user boundaries; synthetic messages excluded from consecutive-role validation; `TauContext.append_synthetic_user()` and `TauContext.cleanup_synthetic()` are public methods for synthetic message operations; `cleanup_synthetic()` removes bridges WITHOUT merging (merge is explicit via `merge_consecutive_assistants()`); **utility functions (`is_synthetic_message`, `make_synthetic_user`, `get_last_real_user_prompt`, `_sanitize_text`, `_sanitize_content`, `_SYNTHETIC_PREFIX`) moved to `agent_message_utils.py` — `agent_context.py` re-exports for backward compatibility** | Structured, consistent recovery; prevents context pollution; proper encapsulation |
| 18.6 | **OpenAI alternation INVARIANT** — `system → user ↔ assistant ↔ tool`; consecutive same-role messages are FORBIDDEN; synthetic bridges are NON-NEGOTIABLE (removing them breaks API compliance); any change bypassing bridges MUST prove alternation is maintained and pass all tests in `test_context_synthetic_bridge.py` + `test_recover_invalid_end_of_turn.py` | Prevents architectural oscillation; enforces API contract |
| 18.7 | **Explicit `merge_consecutive_assistants()`** — `cleanup_synthetic()` removes bridges ONLY (no merge); `merge_consecutive_assistants()` is public and caller-controlled; merges **assistant messages** (content, tool_calls deduplicated by ID, reasoning, refusal, usage_metadata summed); merges **user messages** gracefully (content concatenated, warning logged); does NOT merge tool messages (each has unique tool_call_id); `close_turn()` explicitly calls `merge_consecutive_assistants()` after `cleanup_synthetic()` | **Assistant-only merge was expanded to user merge: synthetic bridges are always user-role messages inserted after assistant messages, so removing them can only create consecutive assistant pairs. Consecutive user messages can also appear from tool-result / post-parse edge cases. Graceful merge prevents crashes while logging warnings for debugging.** Explicit merge chosen over auto-merge and no-merge: auto-merge hides symptoms by embedding policy in cleanup; no-merge ignores the alternation problem entirely. Explicit merge separates data cleanup from policy decision: cleanup removes internal synthetic bridges, merge is a visible, auditable caller-controlled step. Prevents architectural oscillation by making the merge decision explicit and documented. |
| 18.8 | **End-turn recovery redesign** — `_recovery_active` flag (reset at start of `invoke_with_tools_loop()`, set in `_recover_from_missing_end_turn()`); `last_substantive_response` only updates when NOT in recovery mode (prevents recovery responses from clobbering the original); empty responses still trigger recovery; reminder includes first 40 chars preview of stored response; **content-only end-of-turn was REVERTED** (broke subagent tests — subagents returned early without calling `end_turn`) | **Recovery lock prevents the "clobbering bug" where recovery responses overwrote the original good response. Preview in reminder gives the model clear context about what end_turn() resolves to, reducing confusion. Content-only end-of-turn was reverted because it caused subagents to short-circuit the turn loop before completing their work.** The recovery mechanism is a "last resort" for cases where the model keeps failing to call `end_turn`. All responses still require explicit `end_turn` (except via `force_end_turn`). |
| 18.9 | **NO syntax examples in LLM-facing messages** — all messages sent to the LLM (system prompt, tool metadata, recovery reminders, error messages, synthetic user messages) MUST NOT show Python-style function-call syntax like `tool_name(param='value')`. The LLM learns the tool interface from the JSON schema, not from examples. Showing syntax examples creates a contradiction: AGENT.md says "never describe tool calls as plain text" but our examples look exactly like plain-text tool calls. The LLM may try to reproduce the shown syntax as text instead of using the native tool-calling interface, causing malformed tool calls. Use natural language instead: "call the end_turn tool with the message parameter" → "call the end_turn tool with the message parameter". Applies to: `AGENT.md` (system prompt), `tools/end_turn.py` (tool metadata + error messages), `agent_core.py` (recovery reminders), `agent_loop_escalation.py` (escalation messages), `agent_tool_executor.py` (tool errors). Tool error messages describing what the LLM did wrong (e.g., "Original call: tool_name(args)") are acceptable — they describe the error, not teach syntax. | Prevents LLM confusion between natural language instructions and tool-calling syntax; eliminates contradiction with "never describe tool calls as plain text" rule; reduces malformed tool-call output |
| 18.10 | **Escalating end-turn recovery** — `_recover_from_missing_end_turn()` tracks `_cumulative_end_turn_failures` across the entire turn; issues tiered reminders: failures 1-2 (polite reminder), failures 3-4 (critical warning with termination threat), failures 5+ (termination warning demanding immediate `end_turn`); `_cumulative_end_turn_failures` resets at start of each turn; `max_outer_recovery` threshold (5) was NEVER triggered because `outer_recovery_counter` reset to 0 whenever tool calls were present (agent alternated tool calls → plain text → tool calls) | Forceful escalation breaks stubborn verification loops; cumulative counter prevents reset-by-alternation bug |
| 18.11 | **EOT confirmation stack** — EOT logic extracted to `agent_eot_protection.py` (`EOTProtection` class); `TauErgon._eot_protection` instance manages confirmation stack and budget; `EOTProtection.handle_potential_eot()` stacks messages instead of overwriting; `EOTProtection.pop_all_confirmations()` removes all stacked layers at once (both assistant responses and synthetic user messages); `agent_endofturn_validate.py` was removed — implicit structural validation (truncation, unclosed tags, malformed tool calls) was replaced by explicit confirmation-only validation via `EOTProtection.handle_potential_eot()` and `EOTProtection.check_confirmation()` | Stacking preserves full context of the confirmation exchange; prevents losing previous held messages when the LLM keeps responding with plain text; simpler context management (no need to track "first" vs "subsequent" confirmations); removing implicit validation simplifies the codebase and reduces false positives; **EOTProtection extraction** follows established pattern (`agent_init.py`, `agent_session.py`) for isolating subsystems from the god class |
| 18.12 | **Restricted nesting types (T/K) bypass EOT confirmation** — `TauErgon._is_restricted_nesting()` returns True for 'T' (think) and 'K' (skill) nesting types; these types accept plain text responses as end-of-turn WITHOUT requiring the `ENDOFTURN` sentinel; rationale: think/skill forks are bounded computations that should terminate cleanly, not open-ended conversations; the EOT confirmation dance wastes LLM calls and tokens in these restricted contexts; **OpenAI alternation is maintained** — `close_turn()` appends the assistant message before closing | Eliminates unnecessary confirmation rounds for bounded turns; reduces latency and token waste; maintains API compliance |
| 18.13 | **Restricted nesting types (T/K) abort loops at Level 1** — `LoopEscalationManager.handle_loop_escalation()` checks `_is_restricted_nesting()`; if True and `escalation_level >= 1` (3+ warnings), immediately sets `force_end_turn` and returns False; skips the full 5-level escalation ladder; uses `last_substantive_response` as the fallback content; rationale: think/skill forks should fail fast, not go through 15+ warnings of escalating interventions | Prevents wasted computation in bounded turns; think/skill forks have limited scope and should terminate quickly if stuck |
| 18.14 | **Single EOT sentinel (`ENDOFTURN`)** — removed `ENDOFTURN_ALLDONE`, `ENDOFTURN_GIVINGUP`, `ENDOFTURN_` variants; single sentinel `ENDOFTURN` assembled from `_ACCIDENTAL_EOT_PREFIX` at runtime; `check_confirmation()` returns `(bool, stripped_text)` instead of `(status_suffix, stripped_text)`; `accept_confirmation()` takes no parameters; confirmation prompt simplified to single sentinel; rationale: three variants added complexity without meaningful semantic distinction (success vs failure both result in same turn closure); single sentinel reduces prompt size, simplifies LLM instructions, reduces test surface area | Eliminates redundant sentinel variants; simplifies confirmation flow; reduces token usage in prompts; cleaner API (no status suffix needed) |
| 18.15 | **User message prefix protocol** — all user messages prefixed with `[U:TYPE | N:stack]` format; `TauContext` stores `nesting_stack` attribute (e.g., `"0"`, `"F"`, `"S"`, `"SF"`); `append_user(content, user_type="real")` auto-prefixes content; `append_synthetic_user(category, content)` maps category to type (`continuation/turn_started/turn_closed` → `meta`, `eot_confirmation` → `confirm`, `parent_inject` → `inject`, `escalation/recovery` → `system`); `is_synthetic_message()` checks for synthetic types (`meta`, `confirm`, `inject`, `system`) vs non-synthetic types (`real`, `fork`, `subagent`, `redirect`); non-synthetic types preserved by `cleanup_synthetic()`; `get_last_real_user_prompt()` filters by non-synthetic messages; rationale: LLM needs context about message source and nesting level; distinguishes fork/subagent/redirect tasks from real user input; maintains OpenAI alternation while providing semantic clarity | Provides LLM with explicit message provenance; enables proper cleanup_synthetic() behavior (preserves fork/subagent/redirect tasks); simplifies debugging and context analysis; ~20-30 char overhead per message is acceptable |
 | 18.16 | **NO context recovery — fix root cause, never patch** — `attempt_recovery()` was REMOVED from `agent_context_validation.py`; `TauContext.attempt_recovery()` method removed; `context_recovery_display()` removed from console; recovery synthetic bridges (`"recovery"` category) are DEAD CODE. Context validation errors (consecutive same-role messages, unresolved tool calls, tool→user violations) MUST be fixed at their source: compression must preserve alternation, tool execution must maintain assistant→tool→user ordering, EOT flow must not create consecutive users. **Rationale**: Recovery inserts synthetic bridge messages into the middle of context, which breaks the prefix/KV cache — the server can't reuse cached KV pairs from the insertion point forward. Every recovery insertion shifts the serialized JSON body, causing 0% actual cache hit even when 53% of bytes match. Recovery is a band-aid that masks bugs and destroys cache performance. We always address root cause, never patch over broken context. | Prefix cache preservation; forces proper alternation invariant at every mutation point; eliminates O(N) cache degradation from repeated recovery insertions |
 | 18.17 | **SIGINT/Ctrl-C cooperative shutdown (NOT a design change — intentional behavior)** — `AgentLifecycle` class-level flags (`_interrupted`, `_exit_requested`) are shared across ALL agent instances in the same process, including forks and subagents (which run in-process, not subprocess); signal handler registered in `InputHandler._start_input_thread()` implements two-stage shutdown: (1) First Ctrl+C → `set_interrupted(True)` → `close_turn("[Interrupted]")` → `run_loop` returns `None`; (2) Second Ctrl+C → `set_exit_requested(True)` → `close_turn("[Session ended]")` → `run_loop` returns `None`. The `run_loop` function has dual exit-point checks: initial check at top of `while` loop catches exits from previous iteration (e.g. signal received during LLM call), post-control-queue check catches exits from parent supervisor forceful-terminate via A2A control queue. `/exit` command from the LLM is dispatched **within `run_loop`** via `/` prefix detection (`response_text.strip().startswith("/")`) → `_handle_command("exit", ...)` → `set_exit_requested(True)` → `continue` → top-of-loop check catches it. `/exit` from the interactive user is dispatched by `InputHandler._process_input` → same handler. Both paths converge on `_cmd_exit` → `AgentLifecycle.set_exit_requested(True)`. **This behavior is intentional and will NOT be changed** — cooperative shutdown with two-stage interrupt is the correct UX for an agent system. | First interrupt = graceful (let LLM finish current cycle); second interrupt = forceful (abandon immediately); shared class-level flags ensure all in-process forks/subagents respond to the same signal; `/exit` from LLM is a legitimate escape hatch handled in-run-loop, not a separate outer handler |
| 18.18 | **Fork/subagent interruption returns `last_substantive_response`** — when `invoke_fork_sync()` or `invoke_subagent_sync()` detects `run_loop` returned `None` (exit/interrupt), it now returns a descriptive string containing the fork's `last_substantive_response` (if any) instead of `None`; previously `None` propagated through `invoke_with_tools` → `invoke_fork_sync` → fork tool `run()` → `str(None)` = `"None"` as the parent's tool result, which was useless for parent reasoning. The new behavior: if `last_substantive_response` exists, returns `"[Fork/Subagent interrupted — received exit/interrupt signal while working. Last substantive response was: {response}]"`; if no substantive response was produced, returns `"[Fork/Subagent interrupted — received exit/interrupt signal before any substantive response was produced.]"`; the `think` tool benefits automatically since it also calls `invoke_fork_sync`. The delegate command's retry logic is unaffected — it calls `invoke_with_tools` directly (not `invoke_fork_sync`), so `result is None` still triggers retries. | Parent agent can act on the fork's partial work instead of seeing "None"; prevents tool result degradation to `str(None)`; maintains backward compatibility with delegate retry logic; think tool gets the fix for free |
| 18.19 | **Self-confirming ENDOFTURN** — When the LLM returns plain text ending with the `ENDOFTURN` sentinel outside a confirmation round, the turn ends immediately without injecting a confirmation request; the sentinel is stripped and preceding content is used as the final response; audit event `EOT_SELF_CONFIRMED` is emitted; `last_substantive_response` is also stripped of the sentinel to prevent leakage into fallback paths; rationale: eliminates one round-trip (one LLM call + tokens) when the model already intends to end the turn; reduces latency and cost; preserves two-round safety net for ambiguous responses (plain text without sentinel) | Eliminates unnecessary confirmation round for the common case; preserves two-round safety net for ambiguous responses; sentinel stripped from `last_substantive_response` to prevent leakage into budget-exhaustion fallback |

## Configuration (4)

| # | Decision | Rationale |
|---|----------|-----------|
| 19.1 | **`LLMGroup` for multi-LLM support** — named groups with independent model, api_base, params; switchable via `--llm` CLI flag or `/llm` command | Flexible deployment |
| 19.2 | **Environment variable overrides** (`TAU_*` prefix) — all config keys overridable via environment variables | Deployment flexibility |
| 19.3 | **Config resolution order** — `tau.json` → env overrides → dataclass defaults | Predictable precedence |
| 19.4 | **`PathSecurityConfig`** — configurable path whitelist for sandbox validation via `allowed_paths` in config | Flexible sandbox boundaries |

## Logging & Disk Management (2)

| # | Decision | Rationale |
|---|----------|-----------|
| 20.1 | **No log rotation** — audit logs and context files are never rotated, deleted, or compressed by the system | Simplicity, no data loss risk, operator responsibility |
| 20.2 | **Oversized tool output to disk** — `write_oversized_output()` stores large outputs in `LOG_DIR`, context stays small | Disk backup, token economy |

## Model Health (3)

| # | Decision | Rationale |
|---|----------|-----------|
| 21.1 | **`ModelHealthMonitor` circuit breaker** — `agent_model_health.py` tracks LLM server health via `CircuitState` (closed/open/half_open); blocks calls when circuit is open, tests recovery in half_open state | Prevents cascading failures during server outages |
| 21.2 | **`HealthStatus` sliding window** — tracks consecutive failures/successes, total counts, last error timestamps; configurable thresholds via `HealthMonitorConfig` | Granular health observability |
| 21.3 | **`get_health_monitor()` singleton** — per-`base_url` monitor instance; `reset_health_monitor()` for manual reset; dashboard export to disk | Centralized health tracking without global state |

## Phantom Detection (3)

| # | Decision | Rationale |
|---|----------|-----------|
| 22.1 | **Phantom tool call detection** — `agent_phantom_detect.py` detects tool-call-like XML tags that postparse missed; raises `InvalidReplyError` to trigger retry | Catches LLM-generated fake tool calls before they pollute context |
| 22.2 | **Configurable rules via `phantom_rules.json`** — `PhantomRules` dataclass: suffix/prefix patterns, command keywords, whitelist tags, confidence threshold; loaded from file with graceful fallback | Adaptable detection without code changes |
| 22.3 | **Levenshtein scoring** — `_score_phantom()` computes edit distance against known tool names; confidence threshold filters false positives | Precision over recall for phantom detection |

## Privacy & Anonymization (2)

| # | Decision | Rationale |
|---|----------|-----------|
| 23.1 | **No personal information in project files** — skills, source code, task files, documentation, and all other project artifacts must NEVER contain real timestamps, user names, email addresses, personal paths, or any identifying information outside the project | Privacy protection; project remains shareable and anonymous |
| 23.2 | **`$HOME` over literal paths** — use `$HOME` or relative paths instead of `/home/alangeb`; `alangeb` is the only acceptable personal reference and only in `$HOME` context, and even that should be avoided where possible | Path portability; eliminates user identity from codebase |

## Audit Logging (12)

| # | Decision | Rationale |
|---|----------|-----------|
| 24.1 | **Structured audit log format** — `[TIMESTAMP] RECORD_TYPE nesting=N field1=value1 field2=value2` with `  | ` continuation lines; human-readable, machine-parseable, append-only | Single source of truth for debugging, post-mortem, and LLM learning |
| 24.2 | **NEVER TRUNCATE** — all content logged in full; no character/byte/line limits on audit records | Complete fidelity for post-mortem analysis |
| 24.3 | **NEVER ROTATE** — audit file grows for session lifetime; no rotation/archival/compression | Simplicity, no data loss risk, operator responsibility |
| 24.4 | **NEVER REVERT** — append-only; once written, immutable; corrections are new records | Audit trail integrity |
| 24.5 | **`AuditWriter` with buffering** — in-memory buffer flushed on fork/subagent boundaries; single atomic `os.write()` per flush | Concurrency safety without file locking |
| 24.6 | **`ErrorRateTracker`** — thread-safe sliding window error rate tracking with burst detection and alert thresholds | Proactive error monitoring without external dependencies |
| 24.7 | **Console-to-audit bridging** — `agent_audit_bridge.py` provides module-level singleton for console→audit log flow; `emit_console_warning()` delegates to audit writer | Unified observability across console and audit |
| 24.8 | **Nesting level tracking** — `nesting=N` on every record; incremented/decremented by fork/subagent start/end; underflow protection | Traceability across fork/subagent boundaries |
| 24.9 | **Fork audit inheritance** — `TAU_PARENT_AUDIT_FILE` env var allows forks to inherit parent's audit file path; `TAU_FORK_NESTING` sets initial nesting level | Continuous audit trail across process boundaries |
| 24.10 | **Dual API abandoned** — v2 methods (`user_manual`, `user_synthetic`, `assistant_response`, `compress_result`, etc.) were created for richer metadata but never wired into production code. Removed as dead code. The v1 API (`user`, `assistant`, `compress_action`) remains the sole interface | Migration path was abandoned; v2 was dead code from creation |
| 24.11 | **`agent_console/audit_display.py` parser** — regex-based parser with `AuditRecord` dataclass; supports `short`/`long`/`full` display modes; stream-safe iterator for large files | Flexible audit log consumption |
| 24.12 | **Audit file path resolution** — priority: explicit parameter → `TAU_PARENT_AUDIT_FILE` (fork) → `TAU_AUDIT_LOG_FILE` (env) → `LOG_DIR/{SESSION_PREFIX}.audit` (default) | Predictable file location with fork inheritance |

## Dream Orchestration (8)

| # | Decision | Rationale |
|---|----------|-----------|
| 25.1 | **Dream orchestrator** (`commands/_dream.md`) — self-improvement loop: enables heartbeat, runs 8-step cycle (tasks, re-arch, tests, skills, docs, logs, wiki); endless loop until critical problem | Autonomous self-improvement |
| 25.2 | **Dream cycle steps (8, ordered)** — process tasks → re-arch (x3) → test commands → test sanity → skill maintenance → doc sync → log review → wiki maintenance | Comprehensive self-improvement pipeline |
| 25.3 | **Task lifecycle folders** — `tasks/1_todo/` (waiting), `tasks/2_inprogress/` (active), `tasks/3_done/` (completed), `tasks/3_failed/` (failed) | Clear state machine for task processing |
| 25.4 | **Task ordering by filename** — `sorted(glob("1_todo/*.md"))` processes tasks in lexicographic order; `TASK_##.md` naming ensures numerical ordering | Predictable execution sequence |
| 25.5 | **`queue.sh` helper** — auto-generates sequentially numbered task files in `1_todo/` | Task creation convenience |
| 25.6 | **Internal `_tau*` commands** — `/_taudotask`, `/_taurearch`, `/_tautestcommands`, `/_tautestsanity`, `/_tauskillmaintenance`, `/_taudoc`, `/_taulogreview`, `/_tauwiki`; NEVER invoked directly, only via dream.py or `/_dream` | Encapsulated automation pipeline |
| 25.7 | **Dream.py programmatic orchestrator** — handles deterministic ops (file ops, git, testing, timeout, logging); invokes `tau.py` only for LLM-driven work | Separation of deterministic and LLM work |
| 25.8 | **Dream critical rule** — Tau must NEVER perform dream tasks on its own; Dream is ONLY invoked through `dream.py` or `/_dream` | Prevents uncontrolled self-modification |

## Testing & Quality Gates (3)

| # | Decision | Rationale |
|---|----------|-----------|
| 26.1 | **sanity.sh is the gold standard — MUST pass 100%** — `sanity.sh` is the only automated gate between broken code and production; tests CLI, positional args, tool calling, fork functionality, continue command, and other critical paths; **zero failures, zero exceptions, no partial passes**; "pre-existing error" or "not caused by current edits" is **NOT a valid excuse** — if sanity.sh fails, STOP ALL OTHER WORK and fix the root cause; you cannot move forward on ANY task until sanity.sh passes 100% | sanity.sh is the only end-to-end verification; a single failure means something fundamental is broken; patching around failures or blaming the model compounds technical debt |
| 26.2 | **NEVER modify sanity.sh tests, prompts, or expectations** — tests are deliberately crafted and immutable; when sanity.sh fails, the correct response is: investigate the failure, find the root cause in the code, fix the code, re-run; **never assume model failure** — model failures are symptoms, not root causes; always investigate the code path that caused the failure | Immutable tests ensure consistent verification; changing tests to make them pass hides real bugs; model failures are often caused by code issues (context corruption, malformed tool schemas, etc.) |
| 26.3 | **AGENT.md must NEVER reference slash commands (`/fork`, `/status`, etc.)** — slash commands are CLI-level constructs for human users; the agent uses tools (e.g., `fork`, `subagent`, `bash`); if the agent outputs `/fork` as text, it will NOT be executed — it will just be plain text; AGENT.md must use explicit tool references only | Slash commands are parsed by the CLI before reaching the agent; the agent has no access to slash commands; referencing them in the system prompt causes the model to output invalid text instead of using the tool-calling interface |

## Context Sequence Rules (5)

| # | Decision | Rationale |
|---|----------|-----------|
| 27.1 | **Strict OpenAI message alternation** — Context MUST always follow: `system → user → assistant → (tool)* → assistant → user → ...` cycle. No exceptions. Tool results must always be followed by an assistant message before any user message. | OpenAI API enforces this; violating it causes 400 errors or undefined model behavior |
| 27.2 | **No synthetic bypass** — Synthetic messages do NOT bypass alternation rules. If context ends with tool results, a synthetic assistant message MUST be added before any synthetic user message. The validation rule `last_role == "tool" and role == "user"` applies to ALL messages, synthetic or not. | Synthetic messages are system-injected but still must maintain valid alternation; bypassing rules creates fragile code that breaks when validation changes |
| 27.3 | **Full bridge requirement** — When injecting a synthetic user message after tool results OR after any user message (real or synthetic), always add a synthetic assistant bridge first. The bridge can be minimal (e.g., `"[Processing new input...]"`) but MUST be present. Use `append_synthetic_user_with_bridge()` for atomic correctness. | Maintains alternation compliance without manual bookkeeping; prevents context corruption; eliminates consecutive user message warnings |
| 27.4 | **Root cause fixes only** — Never fix symptoms by relaxing validation rules. Always fix the code that creates invalid context. The goal is to never break context in the first place. If validation fails, the caller is at fault, not the validator. | Symptom fixes compound technical debt; root cause fixes prevent future bugs |
| 27.5 | **Bridge helper method** — `TauContext.append_synthetic_user_with_bridge()` appends both the assistant bridge and user message atomically, ensuring alternation compliance. All callers that inject synthetic user messages should prefer this helper. | Single source of truth for bridge logic; prevents caller mistakes |
