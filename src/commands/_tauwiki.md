---
description: Wiki maintenance — ingest unprocessed sessions, maintain structure (also load: wiki)
---

# Wiki Maintenance Command

## Purpose
Ingest unprocessed sessions, maintain wiki structure, fix issues.

## Process
1. Load wiki skill using the `skill` tool
2. Get wiki path: `wiki get`
3. Check for unprocessed sessions in `$HOME/.local/tau/log/`
4. Ingest new sessions (topic-aware, merged by topic)
5. Run wiki maintenance (fix links, split oversized, rebalance)
6. Report stats

## Instructions

Use the `fork` tool to run wiki maintenance:

```
1. Get wiki path: wiki get
2. Check $HOME/.local/tau/log/ for unprocessed sessions
3. For each unprocessed session group:
   - Read audit file
   - Extract user prompts, assistant conclusions, errors
   - Determine topic (tau, swe, book, dream, llm, general)
   - Copy to references/ or _dump/ (safe move protocol)
   - Create/update topic file (merged by topic)
   - Update INDEX.md
   - Delete originals
4. Run maintenance:
   - Fix broken links
   - Split oversized files (> 5kb)
   - Rebalance folders (> 20 entries)
   - Handle orphaned references
5. Report: sessions processed, files created, issues found
```

## Notes
- Use safe move protocol (copy → ingest → confirm → delete)
- Merge sessions on same topic into single file
- Create topic folders dynamically (don't pre-create)
- Trivial sessions → _dump/
- Valuable sessions → references/ + wiki content
- Wiki path is configurable via `wiki get` (default: $HOME/.local/tau/wiki)
- Wiki path can be set via tau.json (wiki.path) or TAU_WIKI_DIR env var
