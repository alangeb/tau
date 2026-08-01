---
name: wiki
description: Local LLM-searchable wiki — store, retrieve, organize, maintain knowledge (also load: dream, idea, task, task_creation, web-research, documentation, graphify, tau_audit)
category: knowledge
keywords: wiki, knowledge base, store information, retrieve knowledge, maintain wiki, local wiki, wiki add, wiki search, wiki maintain, wiki structure, wiki organize, session ingest, audit ingest, query, lint, ingest, maintain, cleanup
---

# Wiki Skill

## When
"store information", "add to wiki", "search wiki", "wiki structure", "retrieve knowledge", "wiki add", "wiki search", "knowledge base", "wiki maintenance", "wiki ingest", "wiki lint"

## Configuration
**Path:** `tau.json` → `"wiki": {"path": "/path/to/wiki"}` | Env: `TAU_WIKI_DIR` | Default: `$HOME/.local/tau/wiki`
- `wiki get` — current path | `wiki set path=/new` — change | `wiki status` — check
- Tau AUTHORIZED to read/write wiki. No user permission required.

## Structure
```
<wiki-root>/
├── INDEX.md                  # Root index
├── log.md                    # Chronological append-only log
├── <topic>/                  # Topic folders (dynamic)
│   ├── INDEX.md
│   └── <topic>-YYYY-MM-wNN.md  # Weekly merged content
├── queries/                  # Query results
├── references/               # Valuable raw source material
└── _dump/                    # Trivial/low-value sessions
```

## Content File Format
```yaml
---
type: session|query|decision|reference|playbook   # REQUIRED
title: One-line summary
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
contradicts: /path/to/contradicting.md            # Optional
---
```

**Body:** `# Title` → `## Session PID` → `### User Prompts` → `### Conclusions` → `### Tools Used` → `### Errors`
**Append:** `## Updates` → `### YYYY-MM-DD: Description`

## Activities

### ADD
1. `git pull origin master`
2. Search existing wiki (INDEX + grep) for overlapping topics
3. Topic exists → append | New topic → create file + folder
4. Update INDEX.md + log.md
5. `git add -A && git commit && git push origin master`
6. Verify: `git status --short` empty

### RETRIEVE
1. INDEX.md keyword search first
2. Content file grep fallback
3. If findability improved → update INDEX + git

### QUERY
1. Search wiki, synthesize answer
2. Valuable answer → file to `queries/` with `type: query`
3. Update INDEX.md + log.md + git

### INGEST
1. `git pull origin master`
2. List `$HOME/.local/tau/log/` → group by `PID_TIMESTAMP`
3. Valuable → `references/` + wiki content | Trivial → `_dump/`
4. Safe move: Copy → Verify → Delete originals
5. Update INDEX.md + log.md + git
- Extract from context files (JSON). Score topics by keyword frequency. Merge same-topic sessions into weekly file.
- Trivial: 1-turn, no errors, no decisions, no insights → `_dump/`

### LINT
1. All `.md` have frontmatter with `type`
2. All cross-refs point to existing files
3. Flag contradictions, stale claims, orphans
4. Update log.md + git

### MAINTAIN
1. `git pull origin master`
2. Walk tree — fix broken links, check file sizes
3. Split files > 5kb | Rebalance INDEX > 20 entries
4. Handle orphans | Update dates | Verify sources
5. Update log.md + git

## Git Integration
**Remote:** `ssh://git@git:/git/wiki` | **Branch:** master
- Every session: `git pull` → work → `git add -A && git commit && git push` → verify clean
- Merge conflicts: prefer MORE data. Keep both. Never delete data.
- Never `git rm` content. Never force-push. References + `_dump/` immutable.

## Helper Scripts
```bash
python3 skills/wiki/wiki_tree.py          # Walk tree, report stats
python3 skills/wiki/wiki_validate.py      # Validate INDEX, find broken links
python3 skills/wiki/wiki_orphans.py       # Find orphaned references
python3 skills/wiki/wiki_ingest.py        # Find unprocessed sessions
python3 skills/wiki/wiki_extract.py       # Extract from context files
python3 skills/wiki/wiki_migrate.py       # Migrate to new spec
python3 skills/wiki/wiki_reprocess.py     # Re-process sessions
python3 skills/wiki/wiki_split.py         # Find oversized files
```

## Dream Integration
Wiki maintenance = step 8 in dream.py cycle.

## Related Skills
- `dream` — orchestrator (wiki = step 8)
- `task` — task lifecycle
- `task_creation` — queue wiki tasks
- `web-research` — source material
- `documentation` — docs vs wiki
- `graphify` — knowledge graphs
- `tau_audit` — audit log analysis
