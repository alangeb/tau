---
category: knowledge
description: "Store and search knowledge in wiki, reference topics, ingest sessions, maintain INDEX and log files (also load: documentation, grep_tool, web-research, task)"
keywords: wiki, knowledge storage, topic search, session ingest, wiki lint, INDEX maintenance, wiki structure, knowledge base
name: wiki
---
## When
"store information", "add to wiki", "search wiki", "wiki structure", "retrieve knowledge", "wiki add", "wiki search", "knowledge base"
## Configuration
**Path:** `tau.json` → `"wiki": {"path": "/path/to/wiki"}` | Env: `TAU_WIKI_DIR` | Default: `$HOME/.local/tau/wiki`
- `wiki get` — current path | `wiki set path=/new` — change | `wiki status` — check
## Structure
```
<wiki-root>/
├── INDEX.md                  # Root index
├── log.md                    # Chronological append-only log
├── <topic>/                  # Topic folders (dynamic)
│   ├── INDEX.md
│   └── <topic>-YYYY-MM-wNN.md  # Weekly merged content
├── queries/ | references/ | _dump/   # Queries, raw sources, trivial sessions
```
## Content File Format
```yaml
---
type: session|query|decision|reference|playbook   # REQUIRED
title: One-line summary | tags: [tag1, tag2] | created: YYYY-MM-DD | updated: YYYY-MM-DD
contradicts: /path/to/contradicting.md            # Optional
---
```
**Body:** `# Title` → `## Session PID` → `### User Prompts` → `### Conclusions` → `### Tools Used` → `### Errors`
## Activities
### ADD
1. `git pull origin master`; search INDEX + grep; append or create; update INDEX.md + log.md + git
### RETRIEVE
1. INDEX.md keyword search first; content file grep fallback
### QUERY
1. Search wiki, synthesize; valuable → `queries/` with `type: query`; update INDEX.md + log.md + git
### INGEST
1. `git pull origin master`; list `$HOME/.local/tau/log/` → group by `PID_TIMESTAMP`
2. Valuable → `references/` | Trivial → `_dump/`; safe move: Copy → Verify → Delete originals
3. Extract from context files (JSON). Score by keyword freq. Merge same-topic into weekly file
### LINT
1. All `.md` have frontmatter + `type`; cross-refs valid; flag contradictions, stale claims, orphans
### MAINTAIN
1. `git pull origin master`; walk tree — fix broken links, check sizes
2. Split files > 5kb | Rebalance INDEX > 20 entries; handle orphans, update dates, verify sources
## Git Integration
**Remote:** `ssh://git@git:/git/wiki` | **Branch:** master
- Merge conflicts: prefer MORE data. Keep both. Never `git rm` content. Never force-push. References + `_dump/` immutable.
## Helper Scripts
```bash
python3 skills/wiki/wiki_tree.py              # Show wiki structure
python3 skills/wiki/wiki_validate.py           # Validate wiki entries
python3 skills/wiki/wiki_orphans.py            # Find orphaned entries
python3 skills/wiki/wiki_ingest.py <file>      # Ingest content
python3 skills/wiki/wiki_extract.py <topic>    # Extract topic
python3 skills/wiki/wiki_migrate.py            # Migrate wiki format
python3 skills/wiki/wiki_reprocess.py          # Reprocess entries
python3 skills/wiki/wiki_split.py <file>       # Split large entries
```
## Related Skills
- `documentation` — docs vs wiki
- `dream` — orchestrator (wiki = step 8)
- `graphify` — knowledge graphs
- `idea` — idea capture
- `sum` — State summarization
- `task` — task lifecycle
- `task` — queue wiki tasks
- `tau_audit` — audit log analysis
- `web-research` — source material
