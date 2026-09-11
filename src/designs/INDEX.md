# Designs Index

Design documents for TauErgon. See `../TAU.md` for the developer guide.

| Document | Content |
|----------|---------|
| [A2A_PROTOCOL.md](A2A_PROTOCOL.md) | Agent-to-agent communication via Unix sockets: message types, constants, session discovery |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Request flow, module dependencies, LLM pipeline, architectural patterns |
| [COMMANDS.md](COMMANDS.md) | Three-tier command dispatch, implementation guide |
| [CONTEXT.md](CONTEXT.md) | Context management patterns, subagent invocation, error handling |
| [DECISIONS.md](DECISIONS.md) | 238 design decisions across 28 categories |
| [DELEGATE.md](DELEGATE.md) | Delegate mode: orchestrator loop, tool restrictions, loop mechanics |
| [EOT.md](EOT.md) | End-of-turn contract: states, transitions, sentinel, confirmation, invariants |
| [INPUT_PROTOCOL.md](INPUT_PROTOCOL.md) | CLI input handling: `#`/`#!` multiline, `!` shell, `+` steering, `/` commands |
| [SKILLS.md](SKILLS.md) | Skill contract, implementation guide |
| [TESTING.md](TESTING.md) | Manual testing, unit tests, e2e tests, test rules |
| [TOOLS.md](TOOLS.md) | Tool contract, implementation rules, common patterns |
