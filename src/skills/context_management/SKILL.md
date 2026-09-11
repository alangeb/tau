---
category: development
description: "Manage context files and memory, reduce token usage, prevent overflow — delegate via subagent/fork (also load: delegation, error-recovery, info, manifest, sum, think)"
keywords: context file, context management, token management, context usage, reduce context, output size control, context overflow prevention, token optimization, context window, conversation compression, token budget, context injection
name: context_management
---

# Context Management

## When
"context full" | "context overflow" | "token limit" | "context usage" | "compression" | "token count" | "code review" | "review code" | "context file" | "compress context" | "token budget" | "inject content" | "context window" | "conversation history"

## Facts
- Location: `~/.local/tau/` — conversation state, summaries, memories
- Format: JSON lines or plain text with YAML frontmatter
- Max size: Keep under 100KB; rotate when larger
- Token estimate: ~1 token per 4 chars; ~1.3 tokens per word

## Monitor
```
info  # Token Usage: XXXXX / 180000 tokens (XX%)
```

### Token Budget
```
Safe: <50% | Warning: 50-70% | Critical: >70%
```

### pyscan Size Guide
- `< 50 files`: `pyscan(path=".")` — full output fine
- `50-200 files`: `pyscan(path=".", compact=True)`
- `> 200 files`: `pyscan(path=".", compact=True, max_files=20)`
- Truncated: follow 💡 Tip in truncation warning

## Operations
```bash
# List context files
ls -la ~/.local/tau/*.json ~/.local/tau/*.md 2>/dev/null
# Compress — use sum skill, then file_append summary
# Inject content
file_append(file_path="<context_file>", content="<compressed_summary>")
# Rotate — archive and truncate to last 500 lines
cp <f> <f>.bak.$(date +%Y%m%d) && tail -500 <f> > <t> && mv <t> <f>
```

## Helpers
```bash
python3 skills/context_management/delegation.py  # Delegation analysis
source skills/context_management/context_check.sh  # Context capacity check
python3 skills/context_management/context_files_helper.py analyze <file>     # Analyze size/tokens
python3 skills/context_management/context_files_helper.py estimate <text>    # Estimate tokens
python3 skills/context_management/context_files_helper.py compress <f> <N>   # Truncate to N lines
```

## Related Skills
- `delegation` — choose subagent vs fork vs background
- `background` — async task execution
- `info` — agent status and context usage
- `error-recovery` — handle tool errors
- `performance` — profile bottlenecks and optimize
- `plan_template` — delegate planned tasks
- `docker` — delegate container tasks
- `think` — fork vs subagent vs think
- `prompt-crafting` — delegation quality
- `sum` — session state summarization
