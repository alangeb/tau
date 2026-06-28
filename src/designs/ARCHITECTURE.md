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
3. **Input**: `InputHandler` (`agent_input.py`) reads stdin/CLI args, dispatches to agent
4. **Loop**: `invoke_with_tools_loop` calls LLM, processes reply, executes tools, repeats
5. **Reply**: 3-stage pipeline (validate → postparse → execute)
6. **Tools**: Signal-based timeout execution with validation, error handling, oversized output to disk
7. **Response**: Final text returned to user, context updated

## Module Dependencies

```
agent_core.py (TauErgon)
├── agent_session.py (AgentSessionManager, TokenTracker)
├── agent_audit_writer.py (AuditWriter, ErrorRateTracker, _classify_error)
│   ├── agent_audit_bridge.py (console-to-audit bridging)
│   ├── agent_token_tracker.py (token counting, cache tracker integration)
│   └── agent_version.py (version detection: VERSION file, git branch/hash)
├── agent_message_utils.py (message utilities: sanitization, synthetic protocol, text extraction — zero agent-module deps)
├── agent_context.py (TauContext)
│   └── agent_context_compress.py (9 compression algorithms)
├── agent_llm.py (facade — re-exports from focused sub-modules)
│   ├── agent_llm_models.py (data structures: ToolCall, Message, LLMResponse, etc.)
│   ├── agent_llm_cache.py (CacheTracker, prefix cache hit tracking)
│   ├── agent_llm_validation.py (reply validation: empty, phantom, tool-call JSON)
│   ├── agent_llm_client.py (SimpleOpenAIClient, HTTP transport, error mapping)
│   ├── agent_llm_invoke.py (_invoke_llm_with_retry, context overflow handling)
│   ├── agent_llm_tool_parse.py (constants, regex patterns, postparse tool-call extraction)
│   ├── agent_model_health.py (ModelHealthMonitor, circuit breaker for LLM health)
│   └── agent_phantom_detect.py (phantom tool call detection & stripping)
├── agent_tool_executor.py (tool execution)
│   └── agent_tool_filter.py (allowlist/blocklist filtering)
├── agent_subagent.py (fork/subagent)
│   └── agent_a2a.py (A2A protocol)
├── agent_input.py (InputHandler)
├── agent_console_primitives.py (Console: _cw, _role_color, Colors, echo, blank_line, etc.)
├── agent_console.py (Console facade — re-exports from messages + display)
├── agent_console_messages.py (Console: declarative message templates)
├── agent_console_display.py (Console: complex display functions)
├── agent_console_audit.py (Console: audit log display)
├── agent_command_handlers.py (@_command decorator, registry, and CommandHandlersMixin)
├── agent_commands.py (CommandManager, three-tier dispatch)
│   └── agent_command_registry.py (unified .py/.md command discovery, caching)
├── agent_loop_detect.py (LoopDetector)
├── agent_loop_escalation.py (LoopEscalationManager)
│   └── agent_reflection.py (ReflectionScheduler)
├── agent_endofturn_validate.py (end-of-turn validation)
├── agent_heartbeat.py (HeartbeatManager)
├── agent_lifecycle.py (AgentLifecycle)
├── agent_plugin_loader.py (dynamic module loading)
├── agent_config.py (Config loading)
├── agent_models.py (InputMessage, SubAgentResult, Colors)
├── agent_init.py (AgentInitConfig, resolve_agent_init)
└── lib/skill_discovery.py (SkillInfo, discover_skills, skill_name_from_path)
```

## Module Reference

| Module | Responsibility |
|--------|----------------|
| `agent_core.py` | `TauErgon` orchestrator — owns context, LLM, tools, loop detection, subagents |
| `agent_message_utils.py` | Pure utilities: `_SYNTHETIC_PREFIX`, `is_synthetic_message()`, `make_synthetic_user()`, `get_last_real_user_prompt()`, `_sanitize_text()`, `_sanitize_content()` — zero agent-module dependencies |
| `agent_context.py` | `TauContext` — conversation context management, validation, compression coordination (imports utilities from `agent_message_utils`) |
| `agent_context_compress.py` | 11 sequential compression algorithms with fixed 50% boundary |
| `agent_llm.py` | Facade — re-exports from focused sub-modules |
| `agent_llm_models.py` | Data structures: ToolCall, Message, LLMResponse, API errors |
| `agent_llm_cache.py` | CacheTracker, prefix cache hit tracking |
| `agent_llm_validation.py` | Reply validation: empty, phantom, tool-call JSON |
| `agent_llm_client.py` | SimpleOpenAIClient, HTTP transport, error mapping |
| `agent_llm_invoke.py` | _invoke_llm_with_retry, context overflow handling |
| `agent_llm_tool_parse.py` | Tool-call parsing engine: constants, 13 regex patterns, kind-specific handlers, `llm_postparse()` |
| `agent_model_health.py` | `ModelHealthMonitor` — circuit breaker pattern for LLM server health; tracks consecutive failures/successes, exponential backoff, connection checks |
| `agent_phantom_detect.py` | `PhantomRules`, `detect_phantoms()`, `strip_phantoms()` — fuzzy detection of tool-call-like XML tags that were not extracted by postparse; configurable via `phantom_rules.json` |
| `agent_a2a.py` | Agent-to-Agent protocol via Unix domain sockets |
| `agent_subagent.py` | Fork/subagent spawning with nesting depth enforcement |
| `agent_tool_executor.py` | Tool execution with signal-based timeout (primary) or thread-based timeout (fallback); validation, error handling, oversized output to disk |
| `agent_endofturn_validate.py` | End-of-turn validation: unclosed tags, malformed tool-call syntax |
| `agent_input.py` | `InputHandler` — stdin thread, signal handling, input dispatch |
| `agent_console_primitives.py` | Console primitives — `_cw()`, `_role_color()`, `Colors`, `echo`, `blank_line` |
| `agent_console.py` | Console facade — re-exports from `agent_console_messages.py` and `agent_console_display.py` |
| `agent_console_messages.py` | Console — declarative message templates (`_ConsoleMessage`, `_msg`, ~45 message entries) |
| `agent_console_display.py` | Console — complex display functions (context, status, help, tools, A2A) |
| `agent_console_audit.py` | Console — audit log display |
| `agent_config.py` | Config loading: `tau.json` → env overrides → dataclass defaults |
| `agent_session.py` | Session management, token tracking
| `agent_audit_writer.py` | Audit logging, error rate tracking |
| `agent_loop_detect.py` | Shannon entropy + repeat count loop detection |
| `agent_models.py` | `InputMessage`, `SubAgentResult`, `Colors` |
| `agent_audit_bridge.py` | Console-to-audit bridging |
| `agent_command_handlers.py` | `@_command` decorator, `_COMMAND_REGISTRY`, query functions (`get_command_info`, `get_builtin_cmd_names`, `get_primary_command_info`), and `CommandHandlersMixin` with all handler methods — self-contained builtin command module |
| `agent_command_registry.py` | Unified `.py`/`.md` command discovery, caching, resolution |
| `agent_commands.py` | `CommandManager`, three-tier dispatch (`.py` → builtin → `.md`) |
| `agent_heartbeat.py` | Idle detection, configurable interval |
| `agent_init.py` | `AgentInitConfig`, `resolve_agent_init()` — init config resolution |
| `agent_lifecycle.py` | System-wide shutdown flags |
| `agent_loop_escalation.py` | Escalation handling, reflection injection, recovery |
| `agent_plugin_loader.py` | Dynamic module loading |
| `agent_reflection.py` | Periodic reflection tracking, adaptive intervals |
| `agent_token_tracker.py` | Token counting, cache tracker integration |
| `agent_tool_filter.py` | Allowlist/blocklist filtering with fnmatch wildcards |
| `agent_version.py` | Version detection: reads VERSION file, git branch/hash |
| `lib/skill_discovery.py` | `SkillInfo`, `discover_skills()`, `skill_name_from_path()` — shared skill discovery for tools/skill.py and validate_skills.py |
| `commands/health.py` | `/health` command — model server health monitoring dashboard (status, reset, check) |
| `commands/plan.py` | `/plan` command — direct interface to the plan tool (status, create, add, complete, block, unblock, next) |
| `tools/graph.py` | `Graph`, `GraphBuilder`, `build_graph()` — cross-file call graph construction from AST analysis |
| `tools/lib/cache.py` | `FileCache` — local file-based caching with TTL |
| `tools/lib/html_to_md.py` | `html_to_markdown()`, `extract_main_content()`, `strip_noise()` — HTML-to-markdown conversion pipeline |
| `tools/lib/session_utils.py` | `session_exists()`, `validate_session()`, `capture_pane()`, `strip_ansi()` — tmux session utilities |
| `tools/pygraph.py` | `pygraph` tool — cross-file call graph queries (callers, callees, path, impact, god, summary) |
| `tools/pyscan.py` | `pyscan` tool — AST-based Python project structure analysis |
| `tools/pyanalyze.py` | `pyanalyze` tool — unused function and import detection |
| `tools/pycheck.py` | `pycheck` tool — missing/unused import checking |
| `tools/plan.py` | `plan` tool — hierarchical task plan management (create, add, complete, block, unblock, status, next, progress, update, delete, clear) |
| `validate_skills.py` | Skill validation script — checks frontmatter, structure, and cross-references |
| `validate_tools.py` | Tool validation script — checks tool module structure |

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
