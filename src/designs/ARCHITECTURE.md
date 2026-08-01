# Architecture — TauErgon

## Request Flow

A request flows through the system in this order:

```
CLI args → Config load → TauErgon init → InputHandler → invoke_with_tools_loop
                                                        ↓
                                              LLM call (agent_llm_invoke.py)
                                                        ↓
                                            agent_llm_client.py (HTTP client)
                                                        ↓
                                            3-stage reply processing
                                                        ↓
                                          Tool execution (sequential)
                                                        ↓
                                                Response → User
```

1. **CLI**: `tau.py` parses args, loads config (`agent_config.py`), validates LLM group
2. **Init**: `TauErgon` creates context, LLM client, tool registry, loop detector, A2A server
   - A2A server enables inter-agent communication; see [A2A_PROTOCOL.md](A2A_PROTOCOL.md) for the full contract
3. **Input**: `InputHandler` (`agent_input.py`) reads stdin/CLI args, dispatches to agent
4. **Loop**: `invoke_with_tools_loop` calls LLM, processes reply, executes tools, repeats
5. **Reply**: 3-stage pipeline (validate → postparse → execute)
6. **Tools**: Signal-based timeout execution with validation, error handling, oversized output to disk
7. **Response**: Final text returned to user, context updated

## Module Dependencies

```
agent_core.py (TauErgon)
├── agent_session.py (AgentSessionManager — inherits TokenTracker)
│   ├── agent_session_registry.py (SessionRegistry — JSON-based index of session files for archiving, tagging, smart filtering)
│   └── agent_log_cleanup.py (log file management: failed_request.json retention, archival, gzip compression)
├── agent_token_tracker.py (TokenTracker base class — token counting, cache tracker integration)
├── agent_audit_writer.py (AuditWriter, ErrorRateTracker, _classify_error)
│   ├── agent_audit_bridge.py (console-to-audit bridging)
│   └── agent_version.py (version detection: VERSION file, git branch/hash)
├── agent_message_utils.py (message utilities: sanitization, synthetic protocol, text extraction — zero agent-module deps)
├── agent_context.py (TauContext)
│   ├── agent_context_utils.py (shared context-file utilities: format_age, get_all_context_files [uses registry], read_context_metadata, read_context_metadata_for_a2a)
│   ├── agent_context_compress.py (11 compression algorithms)
│   └── agent_context_validation.py (validate_context, validate_on_mutation, get_pending_tool_ids, validate_tool_resolution — extracted validation, zero recovery)
├── agent_llm_models.py (data structures: ToolCall, Message, LLMResponse, etc.)
├── agent_llm_cache.py (PrefixCacheTracker, prefix cache hit tracking)
├── agent_llm_validation.py (reply validation: empty, phantom, tool-call JSON)
├── agent_llm_client.py (SimpleOpenAIClient, HTTP transport, error mapping)
├── agent_llm_invoke.py (_invoke_llm_with_retry, context overflow handling)
├── agent_llm_tool_parse.py (constants, regex patterns, postparse tool-call extraction)
├── agent_model_health.py (ModelHealthMonitor, circuit breaker for LLM health)
└── agent_phantom_detect.py (phantom tool call detection & stripping)
├── agent_tool_executor.py (tool execution)
│   └── agent_tool_filter.py (allowlist/blocklist filtering)
├── agent_subagent.py (fork/subagent)
│   └── agent_a2a.py (A2A protocol)
├── agent_subsystems.py (SubsystemBundle, init_subsystems, read_system_prompt — subsystem init encapsulation)
├── agent_input.py (InputHandler)
├── agent_console/ (Console: audit, primitives, messages, display, audit_display)
├── agent_command_handlers.py (@_command decorator, registry, and CommandHandlersMixin)
├── agent_commands.py (CommandManager, three-tier dispatch)
│   └── agent_command_registry.py (unified .py/.md command discovery, caching)
├── agent_command_dispatcher.py (ContextManager — /ctx, /undo, /continue, /load commands; RestartManager — restart flow with CLI arg preservation)
├── agent_loop.py (run_loop — extracted core LLM tool-calling loop; reduces coupling in agent_core.py)
├── agent_loop_detect.py (LoopDetector)
├── agent_loop_escalation.py (LoopEscalationManager)
│   └── agent_reflection.py (ReflectionScheduler)
├── agent_heartbeat.py (HeartbeatManager)
├── agent_eot_protection.py (EOTProtection — end-of-turn confirmation stack)
├── agent_lifecycle.py (AgentLifecycle)
├── agent_plugin_loader.py (dynamic module loading)
├── agent_config.py (Config loading)
├── agent_models.py (InputMessage, SubAgentResult, Colors)
├── agent_init.py (AgentInitConfig, resolve_agent_init)
└── lib/skill_discovery.py (SkillInfo, discover_skills, skill_name_from_path)
├── tau.py (entry point: CLI parsing, config resolution, A2A CLI mode)
├── validate_skills.py (skill validation: frontmatter, structure, cross-references)
├── validate_tools.py (tool validation: module structure)
├── wiki_batch_ingest.py (wiki batch ingestion: parse context/audit files, detect topics, create wiki content)
├── agent_project.py (project management: find_project_root, init_project, contexts.json tracking)
├── tools/__init__.py (tool discovery, ToolEntry, ToolMetadata, ToolModule protocol, CMD_ALIASES/ARG_ALIASES)
├── tools/validation.py (normalize_tool_call, validate_tool_name, _dataclass_to_json_schema)
├── tools/lib/sandbox.py (check_path, validate_path, get_allowed_paths — path security)
├── commands/delegate.py (delegate mode: LLM-instructed orchestration, DELEGATE_INSTRUCTIONS)
└── commands/ralph.py (iterative task execution with <complete> tag confirmation, state in JSON files)
```

## Module Reference

| Module | Responsibility |
|--------|----------------|
| `agent_core.py` | `TauErgon` orchestrator — owns context, LLM, tools, loop detection, subagents |
| `agent_message_utils.py` | Pure utilities: user message prefix protocol (`[U:TYPE | N:stack]`), `is_synthetic_message()` (type-aware: synthetic types `meta/confirm/inject/system` vs non-synthetic `real/fork/subagent/redirect`), `make_synthetic_user()` (deprecated), `get_last_real_user_prompt()`, `_sanitize_text()`, `_sanitize_content()` — zero agent-module dependencies |
| `agent_context.py` | `TauContext` — conversation context management, validation, compression coordination; `nesting_stack` attribute tracks nesting level; `append_user(content, user_type)` auto-prefixes with `[U:TYPE | N:stack]`; `append_synthetic_user(category, content)` maps category to type |
| `agent_context_utils.py` | Shared context-file utilities: `format_age()`, `get_all_context_files()`, `read_context_metadata()`, `read_context_metadata_for_a2a()` — eliminates duplication across `agent_input`, `agent_project`, `agent_a2a` |
| `agent_context_compress.py` | 11 sequential compression algorithms with fixed 50% boundary |
| `agent_context_validation.py` | `validate_context()`, `validate_on_mutation()`, `get_pending_tool_ids()`, `validate_tool_resolution()` — pure validation on message lists; no recovery (fix root cause only per decision 18.16) |
| `agent_llm_models.py` | Data structures: ToolCall, Message, LLMResponse, API errors |
| `agent_llm_cache.py` | PrefixCacheTracker, prefix cache hit tracking |
| `agent_llm_validation.py` | Reply validation: empty, phantom, tool-call JSON |
| `agent_llm_client.py` | SimpleOpenAIClient, HTTP transport, error mapping |
| `agent_llm_invoke.py` | _invoke_llm_with_retry, context overflow handling |
| `agent_llm_tool_parse.py` | Tool-call parsing engine: constants, 13 regex patterns, kind-specific handlers, `llm_postparse()` |
| `agent_model_health.py` | `ModelHealthMonitor` — circuit breaker pattern for LLM server health; tracks consecutive failures/successes, exponential backoff, connection checks |
| `agent_phantom_detect.py` | `PhantomRules`, `detect_phantoms()`, `strip_phantoms()` — fuzzy detection of tool-call-like XML tags that were not extracted by postparse; configurable via `phantom_rules.json` |
| `agent_a2a.py` | Agent-to-Agent protocol via Unix domain sockets; `A2AServer` handles query/supervise/status connections; `Supervisor` class manages parent-side control (inject, terminate, redirect, loop detection); control queue integration in `agent_core._process_control_queue`. See [A2A_PROTOCOL.md](A2A_PROTOCOL.md) for the full v1.0 contract. |
| `agent_subagent.py` | Fork/subagent spawning with nesting depth enforcement |
| `agent_subsystems.py` | `SubsystemBundle`, `init_subsystems()`, `read_system_prompt()` — encapsulates subsystem creation and wiring; reduces import burden on `agent_core.py`; makes subsystem init testable in isolation |
| `agent_tool_executor.py` | Tool execution with signal-based timeout (primary) or thread-based timeout (fallback); validation, error handling, oversized output to disk |
| `agent_input.py` | `InputHandler` — stdin thread, signal handling, input dispatch |
| `agent_console/` | Console — unified package: audit (console-to-audit bridging), primitives (low-level I/O: echo, status, _cw, prompt), messages (display helpers, _ConsoleMessage class, MessageRegistry + message definitions), display (consolidated display functions), audit_display (audit log viewer with `AuditRecord`, `parse_audit_file`, `show_audit`) |
| `agent_config.py` | Config loading: `tau.json` → env overrides → dataclass defaults |
| `agent_session.py` | Session management, token tracking |
| `agent_log_cleanup.py` | Log file management — `cleanup_failed_requests()` (retention policy for `failed_request.json`), `archive_file()` (move to `dump/`), `compress_file()` (gzip), `merge_small_failed_requests()` (combine small files), `run_full_cleanup()` (orchestrates all operations) |
| `agent_audit_writer.py` | Audit logging, error rate tracking |
| `agent_loop_detect.py` | Shannon entropy + repeat count loop detection |
| `agent_models.py` | `InputMessage`, `SubAgentResult`, `Colors` |
| `agent_audit_bridge.py` | Console-to-audit bridging |
| `agent_command_handlers.py` | `@_command` decorator, `_COMMAND_REGISTRY`, query functions (`get_command_info`, `get_builtin_cmd_names`, `get_primary_command_info`), and `CommandHandlersMixin` with all handler methods — self-contained builtin command module |
| `agent_command_registry.py` | Unified `.py`/`.md` command discovery, caching, resolution |
| `agent_commands.py` | `CommandManager`, three-tier dispatch (`.py` → builtin → `.md`) |
| `agent_command_dispatcher.py` | `ContextManager` (/ctx, /undo, /continue, /load commands); `RestartManager` (restart flow with CLI arg preservation) |
| `agent_loop.py` | `run_loop` — extracted core LLM tool-calling loop from `agent_core.py`; reduces coupling; maintains OpenAI alternation invariant |
| `agent_heartbeat.py` | Idle detection, configurable interval |
| `agent_eot_protection.py` | `EOTProtection` — end-of-turn confirmation stack, budget management, accidental EOT detection |
| `agent_init.py` | `AgentInitConfig`, `resolve_agent_init()` — init config resolution |
| `agent_lifecycle.py` | System-wide shutdown flags |
| `agent_loop_escalation.py` | Escalation handling, reflection injection, recovery |
| `agent_plugin_loader.py` | Dynamic module loading |
| `agent_reflection.py` | Periodic reflection tracking, adaptive intervals |
| `agent_token_tracker.py` | Token counting, cache tracker integration |
| `agent_tool_filter.py` | Allowlist/blocklist filtering with fnmatch wildcards |
| `agent_version.py` | Version detection: reads VERSION file, git branch/hash |
| `lib/skill_discovery.py` | `SkillInfo`, `discover_skills()`, `skill_name_from_path()` — shared skill discovery for tools/skill.py and validate_skills.py |
| `tau.py` | Entry point: CLI parsing, config resolution, A2A CLI mode, `main()` |
| `validate_skills.py` | Skill validation script — checks frontmatter, structure, and cross-references |
| `validate_tools.py` | Tool validation script — checks tool module structure |
| `wiki_batch_ingest.py` | Wiki batch ingestion — parses context/audit files, detects topics, creates wiki content files, updates topic indexes |
| `agent_project.py` | Project management — `find_project_root()`, `init_project()`, `contexts.json` tracking for project-scoped context files |
| `tools/__init__.py` | Tool discovery, `ToolEntry`, `ToolMetadata`, `ToolModule` protocol, `CMD_ALIASES`/`ARG_ALIASES`, `get_all_tools()` |
| `tools/validation.py` | `normalize_tool_call()`, `validate_tool_name()`, `_dataclass_to_json_schema()`, `_validate_tool_args()`, `_generate_validation_error()` |
| `tools/lib/sandbox.py` | `check_path()`, `validate_path()`, `get_allowed_paths()` — path security and working directory boundary enforcement |
| `commands/health.py` | `/health` command — model server health monitoring dashboard (status, reset, check) |
| `commands/plan.py` | `/plan` command — direct interface to the plan tool (status, create, add, complete, block, unblock, next) |
| `commands/delegate.py` | `/delegate` command — ToolFilter enforces read-only behavior at execution time; `_ALLOWED_DELEGATE_TOOLS` allowlist; `DELEGATE_INSTRUCTIONS` injected into context; all tools still announced (prefix cache preserved) |
| `commands/ralph.py` | `/ralph` command — iterative task execution with `<complete>` tag confirmation; maintains task state in JSON files under `~/.local/tau/ralph/` |
| `commands/heartbeat.md` | `/heartbeat` command — automated idle check-in; fork determines if open task needs action (`<PROMPT>`) or nothing (`<NO_ACTION>`) |
| `commands/gitcrit.md` | `/gitcrit` command — multi-stage code review: subagent (pyscan/pyanalyze/review skills) → fork (critique) → fork (cross-reference audit) |
| `commands/pyprep.md` | `/pyprep` command — Python project preparation: runs `info`, `pyscan`, `pyanalyze` on target directory |
| `commands/_dream.md` | `/_dream` command — Dream orchestrator entry point: enables heartbeat, runs self-improvement cycle (tasks, re-arch, tests, skills, docs, logs, wiki) |
| `commands/_taudotask.md` | `/_taudotask` command — execute task from `2_inprogress/` folder (Dream cycle step 1) |
| `commands/_taurearch.md` | `/_taurearch` command — re-architecture pass (Dream cycle step 2) |
| `commands/_tautestcommands.md` | `/_tautestcommands` command — test command suite (Dream cycle step 3) |
| `commands/_tautestsanity.md` | `/_tautestsanity` command — run sanity.sh e2e tests (Dream cycle step 4) |
| `commands/_tauskillmaintenance.md` | `/_tauskillmaintenance` command — periodic skill maintenance (Dream cycle step 5) |
| `commands/_taudoc.md` | `/_taudoc` command — documentation maintenance (Dream cycle step 6) |
| `commands/_taulogreview.md` | `/_taulogreview` command — audit log analysis for errors and improvement opportunities (Dream cycle step 7) |
| `commands/_tauwiki.md` | `/_tauwiki` command — wiki maintenance: ingest sessions, maintain structure (Dream cycle step 8) |
| `commands/_tautest.md` | `/_tautest` command — general testing orchestrator: runs `./tau.py` with parameters, creates test plans, fixes issues found |
| `commands/sum.md` | `/sum` command — context summarization command |
| `tools/graph.py` | `Graph`, `GraphBuilder`, `build_graph()` — cross-file call graph construction from AST analysis |
| `tools/lib/cache.py` | `FileCache` — local file-based caching with TTL |
| `tools/lib/html_to_md.py` | `html_to_markdown()`, `extract_main_content()`, `strip_noise()` — HTML-to-markdown conversion pipeline |
| `tools/lib/session_utils.py` | `session_exists()`, `validate_session()`, `capture_pane()`, `capture_delta()`, `strip_ansi()` — tmux session utilities with delta tracking |
| `tools/pygraph.py` | `pygraph` tool — cross-file call graph queries (callers, callees, path, impact, god, summary) |
| `tools/pyscan.py` | `pyscan` tool — AST-based Python project structure analysis |
| `tools/pyanalyze.py` | `pyanalyze` tool — unused function and import detection |
| `tools/pycheck.py` | `pycheck` tool — missing/unused import checking |
| `tools/plan.py` | `plan` tool — hierarchical task plan management (create, add, complete, block, unblock, status, next, progress, update, delete, clear) |
| `tools/background_capture.py` | `background_capture` tool — capture tmux pane output with scrollback history |
| `tools/background_exec.py` | `background_exec` tool — execute commands in tmux session with optional wait |
| `tools/background_kill.py` | `background_kill` tool — kill tmux sessions |
| `tools/background_ls.py` | `background_ls` tool — list active tmux sessions |
| `tools/background_new.py` | `background_new` tool — create new tmux sessions |
| `tools/background_run.py` | `background_run` tool — run command in background, wait, return output (convenience) |
| `tools/background_send_keys.py` | `background_send_keys` tool — send keystrokes to tmux session |
| `tools/background_wait.py` | `background_wait` tool — wait for tmux session with idle/keyword/prompt detection |
| `tools/bash.py` | `bash` tool — shell command execution with dangerous command detection (`DANGEROUS_PATTERNS`) and double-call confirmation |
| `tools/cd.py` | `cd` tool — change working directory (persistent across tool calls) |
| `tools/crawl.py` | `crawl` tool — website crawler with configurable depth, max pages, domain filtering |
| `tools/fetch.py` | `fetch` tool — web page fetcher (Crawl4AI first-attempt with native HTML-to-markdown fallback) |
| `tools/file_append.py` | `file_append` tool — append content to file; auto-creates parent dirs |
| `tools/file_edit.py` | `file_edit` tool — targeted text replacement with fuzzy matching |
| `tools/file_read.py` | `file_read` tool — read files with line numbers, offset/limit support |
| `tools/file_write.py` | `file_write` tool — create or overwrite files; auto-creates parent dirs |
| `tools/end_turn.py` | `end_turn` tool — signal end of turn; sets `force_end_turn`; resolves empty message to `last_substantive_response`; must be sole tool call in message |
| `tools/fork.py` | `fork` tool — spawn subagent inheriting full parent context |
| `tools/glob.py` | `glob` tool — file pattern matching with recursive search |
| `tools/grep.py` | `grep` tool — regex pattern search with recursive directory support |
| `tools/head.py` | `head` tool — show first N lines of a file |
| `tools/info.py` | `info` tool — agent info: PIDs, context usage, model config, git status |
| `tools/lookup.py` | `lookup` tool — encyclopedic lookup via Wikipedia + DuckDuckGo Instant Answer |
| `tools/ls.py` | `ls` tool — directory listing with formatting options |
| `tools/search.py` | `search` tool — web search via SearXNG → DuckDuckGo → Mojeek cascade |
| `tools/see.py` | `see` tool — load image files for vision model injection |
| `tools/skill.py` | `skill` tool — load skill content and spawn forked subagent with skill instructions |
| `tools/subagent.py` | `subagent` tool — spawn isolated subagent with blank slate context |
| `tools/think.py` | `think` tool — read-only fork for deep analysis (allowlisted tools only) |
| `tools/wc.py` | `wc` tool — count lines, words, and characters in files |
| `tools/wiki.py` | `wiki` tool — manage wiki configuration: get/set wiki path, check wiki status (exists, git status, file count, size) |

## LLM Reply Processing Pipeline

Every LLM response passes through 3 stages:

```
LLM Response
    ↓
Stage 1: Validate (agent_llm_validation.py)
    ↓ InvalidReplyError → retry
Stage 2: Post-parse (agent_llm_tool_parse.py)
    ↓ Extracted tool calls + cleaned content
Stage 3: Execute (agent_tool_executor.py)
    ↓ Tool results appended to context
Loop repeats or returns final response
```

### Stage 1: Validation

`llm_validate(content, reasoning, tool_calls, finish_reason)` checks:
1. Tool-call JSON valid — every `arguments` field is valid JSON
2. Response not empty — content or tool calls present
3. Not cut off — `finish_reason != "length"`

Raises `InvalidReplyError` on failure → triggers retry with backoff.

### Stage 2: Post-parse

`llm_postparse(content, reasoning, tool_calls)` recovers missed tool calls:
- Extracts tool calls from text content using regex patterns
- Handles multiple tag formats: `<function=...>`, `<tool=...>`, `<thinking>...</thinking>`
- Moves enclosed thoughts from content to reasoning field

### Stage 3: Tool Execution

`execute_tool_batch(tool_calls, agent, reasoning, audit_writer)`:
1. Validates args against tool's `Args` dataclass
2. Fixes aliases and coerces types
3. Executes tools sequentially with signal-based timeout (primary) or thread-based timeout (fallback)
4. Appends tool results to context
5. Handles oversized outputs (truncate + disk backup)

**Sequential execution** maintains OpenAI message alternation.

## Key Architectural Patterns

### Stdlib-Only Core

No external dependencies for critical paths. `SimpleOpenAIClient` uses `urllib.request` instead of `requests`.

### Centralized Orchestrator

`TauErgon` owns everything: context, LLM calls, tool execution, subagent spawning. Single ownership → clear responsibility → easier debugging.

### Token Economy

Context compression is a first-class concern. KV cache optimization via right-to-left compression, fixed boundaries, and parameter consistency.

#### Dynamic Compression Thresholds

Compression runs at two points in the agent loop:

1. **Pre-LLM call** (after context validation, before LLM call): Uses dynamic threshold based on `loop_detector.escalation_level`:
   - Level 0 (normal): 85% threshold — same as post-call, no pre-call compression
   - Level 1 (first warning): 65% threshold — compress more aggressively
   - Level 2+ (further escalation): 35% threshold — aggressively compress to break the loop

2. **Post-LLM call** (after LLM response, before appending assistant message): Static 85% threshold as safety net for context growth during the LLM call.

**Rationale**: When the loop is stuck, breaking it takes priority over preserving KV cache. Aggressive compression before the LLM call prevents the model from operating on bloated context — the root cause of many loops. The KV cache loss from compression is acceptable when the alternative is an infinite loop.

### Three Delegation Modes

| Mode | Context | Use When |
|------|---------|----------|
| Subagent | Blank slate | Task is self-contained, needs isolation |
| Fork | Deep copy of parent | Task needs full conversation history |
| Delegate | Same agent, LLM-instructed | Orchestration without context duplication |

### Signal-Based Timeout (Primary)

Tools execute with `signal.setitimer()` + `SIGALRM` handler raising `ToolTimeout`; no daemon threads, no orphaned processes. Thread-based timeout available as fallback when signals unavailable.

### Three-Tier Command Dispatch

`.py` → builtin → `.md` priority allows clean upgrades from simple prompts to full-featured commands.
