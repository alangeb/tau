# TauErgon

[📄 License](LICENSE) · [📋 Disclaimer](DISCLAIMER.md) · [🔒 Security](SECURITY.md)

## ⚠️ Warning

This project is an **experimental AI agent** capable of generating and executing code. It may produce incorrect, unsafe, or incomplete outputs. Always review all outputs before use in production or sensitive environments. Run in a sandboxed environment. Use at your own risk.

See [DISCLAIMER.md](DISCLAIMER.md) for full terms and [SECURITY.md](SECURITY.md) for safe usage guidelines.

---

## What Is TauErgon?

TauErgon is a self-contained AI agent framework with tool calling, context compression, agent delegation, and inter-agent communication. Written in Python using **stdlib only** — zero pip installs required beyond an OpenAI-compatible API endpoint.

### Capabilities

- **33 tools** — file ops, shell, web search, code analysis, background processes, and more
- **Agent delegation** — fork (inherits context), subagent (blank slate), delegate (orchestrator)
- **Context compression** — automatic when approaching token limits
- **Agent-to-Agent (A2A)** — inter-agent communication via Unix domain sockets
- **Loadable skills** — specialized task instructions
- **Extensible commands** — built-in, Python, and Markdown commands
- **Skills system** — 23 pre-built skills for common workflows

---

## Quickstart

### Requirements

- **Python 3.10+** (stdlib only — no pip installs needed)
- An OpenAI-compatible API endpoint (e.g., vLLM, Ollama, llama.cpp)

### Install

```bash
git clone https://github.com/alangeb/tau.git
cd tau
```

Copy and edit `src/tau.json` to configure your LLM endpoint:

```bash
cp src/tau.json src/tau.json.bak   # keep defaults as reference
# Edit src/tau.json — set api_base, model, etc. under llm_groups
```

**Optional:** Install to `~/.local/tau/` for convenience:

```bash
bash install.sh
```

This copies `src/` to `~/.local/tau/` and makes `tau.py` executable. You can then run `~/.local/tau/tau.py` from anywhere.

### Run

```bash
# Interactive mode (reads from stdin)
python src/tau.py

# Non-interactive: pass inputs as arguments
python src/tau.py "Hello, what can you do?"

# Multiple inputs (chained)
python src/tau.py "X=1" "/fork what is the value of X"

# Continue from previous session
python src/tau.py --continue

# Use a specific LLM group
python src/tau.py --llm cuda "Explain quantum computing"
```

---

## Typical Workflows

### Ask a Question

```bash
python src/tau.py "How do I implement a binary search in Python?"
```

### Analyze a Codebase

```bash
python src/tau.py "Analyze the project structure" "/pyprep"
```

### Iterative Development

```bash
# Implement, then fork for review
python src/tau.py "Implement feature X" "/fork review the changes"
```

### Background Monitoring

```bash
# Start agent, keep alive for A2A queries
python src/tau.py --keep-alive "Monitor process PID 1234"

# Query from another terminal
python src/tau.py --pid 1234 --query "What's the status?"
```

---

## Commands

TauErgon has a three-tier command system: **Python** (`.py`) → **built-in** → **Markdown** (`.md`).

### Key Commands

| Command | Description |
|---------|-------------|
| `/fork <task>` | Spawn forked agent with full parent context |
| `/subagent <task>` | Spawn isolated agent (blank slate) |
| `/delegate <task>` | Enter orchestration mode |
| `/status` | Show agent status (context, tokens, model, cache) |
| `/ctx [mode]` | Dump context (`summary`, `tool`, `assistant`, `trace`) |
| `/help` | Show available commands |
| `/tools` | List available tools |
| `/compress` | Force context compression |
| `/exit` | Exit the session |

For the full command reference, see [designs/COMMANDS.md](src/designs/COMMANDS.md).

---

## Tools

33 dynamically discovered tools covering:

- **File operations**: `file_read`, `file_edit`, `file_write`, `glob`, `grep`, `head`, `wc`, `cd`, `ls`
- **Shell & process**: `bash`, `background_*` (tmux session management)
- **Web & search**: `fetch`, `crawl`, `search`, `lookup`
- **Code analysis**: `pyscan`, `pyanalyze`, `pycheck`
- **Agent management**: `info`, `end_turn`, `think`, `skill`, `plan`, `fork`, `subagent`

For tool implementation details, see [designs/TOOLS.md](src/designs/TOOLS.md).

---

## Skills

23 loadable skills for specialized tasks. Agents invoke skills via the `skill` tool, which spawns a forked subagent with the skill content as additional instructions.

Notable skills: `agent-browser`, `ast-grep`, `background`, `code-review-workflow`, `git`, `python_best_practices`, `python_debugging`, `shell_scripting`, `tau_testsuite`, `tool_template`, and more.

For skill implementation details, see [designs/SKILLS.md](src/designs/SKILLS.md).

---

## Configuration

`src/tau.json` controls LLM endpoints, timeouts, compression, and more. Key sections:

- **`llm_groups`** — Named LLM configurations (model, api_base, params)
- **`tool_execution`** — Tool timeouts and polling
- **`loop_detection`** — Repetitive behavior detection
- **`nesting`** — Subagent depth limits
- **`external_services`** — SearXNG, Crawl4AI URLs

Environment variables override any key (prefix: `TAU_`). For the full config reference, see [src/TAU.md](src/TAU.md) and [designs/DECISIONS.md](src/designs/DECISIONS.md).

---

## Design & Architecture

Detailed design documents live in `src/designs/`:

| Document | Content |
|----------|---------|
| [ARCHITECTURE.md](src/designs/ARCHITECTURE.md) | Request flow, module dependencies, pipelines |
| [DECISIONS.md](src/designs/DECISIONS.md) | 167 design decisions across 20 categories |
| [CONTEXT.md](src/designs/CONTEXT.md) | Context management patterns |
| [COMMANDS.md](src/designs/COMMANDS.md) | Command implementation guide |
| [SKILLS.md](src/designs/SKILLS.md) | Skill implementation guide |
| [TESTING.md](src/designs/TESTING.md) | Testing guide |
| [TOOLS.md](src/designs/TOOLS.md) | Tool implementation guide |

---

## Testing

```bash
# Unit tests (pytest)
cd src && pytest

# End-to-end tests (requires LLM endpoint, ~100 seconds)
bash sanity.sh
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE) for full terms.
