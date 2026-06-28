---
name: graphify
description: Turn codebases into persistent knowledge graphs — community detection, query/path/explain. Code graph, knowledge graph, architecture visualization (also load: bug_investigation, web-research, code-review-workflow)
category: analysis
keywords: knowledge graph, code graph, dependency graph, call graph, graph analysis
---

# Graphify

## When
"codebase graph", "knowledge graph", "graphify", "code architecture", "file relationships", "project analysis"

## Fast Path
`graphify-out/graph.json` exists → **skip pipeline, run `graphify query "<question>"` directly.**
No path → `.`. GitHub URL → clone first.

## Pipeline
```bash
python3 skills/graphify/pipeline.py <path> [flags...]  # Run full pipeline
```

### Steps (Manual)
0. **GitHub**: Clone. See `references/github-and-merge.md`.
1. **Install**: Resolve Python interpreter. Install `graphifyy`. Save to `graphify-out/.graphify_python`.
2. **Detect**: `graphify.detect.detect(Path('INPUT_PATH'))` → `.graphify_detect.json`.
   - `total_files=0` → stop. `>2M words` or `>500 files` → narrow scope.
3. **Extract** (parallel AST + semantic):
   - AST: `graphify.extract.extract(code_files)` → `.graphify_ast.json`.
   - Semantic: Subagent dispatch (5-10x faster). Split 20-25/chunk. Prompt: `references/extraction-spec.md`.
   - Merge → `.graphify_extract.json`.
4. **Build**: `build_from_json(extraction, directed=True)` → cluster, score → `graph.json`, `GRAPH_REPORT.md`.
5. **Label**: 2-5 word community names → `.graphify_labels.json`.
6. **Export**: `graphify export html` (default). See `references/exports.md` for formats.
7. **Cleanup**: Remove temp files. Report outputs.

## Flags
| Flag | Purpose |
|------|---------|
| `--mode deep` | Richer INFERRED edges |
| `--update` | Incremental rebuild |
| `--directed` | Preserve edge direction |
| `--no-viz` | Skip HTML |
| `--svg --graphml --neo4j --mcp` | Export formats |
| `--obsidian` | Obsidian vault |
| `--watch --wiki` | Auto-rebuild |

## Query
```bash
graphify query "<question>"                          # BFS
graphify query "<question>" --dfs --budget 1500      # DFS, token cap
graphify path "A" "B"                               # Shortest path
graphify explain "Node"                              # Plain explanation
```

## Honesty Rules
- Never invent edge — use AMBIGUOUS if unsure
- Never skip corpus check warning
- Always show token cost
- Never hide cohesion scores
- Never run HTML viz on >5,000 nodes without warning

## Related Skills
- `bug_investigation` — graph-based bug analysis
- `code-review-workflow` — uses pyscan/pygraph for Python projects (sibling)
- `web-research` — graphify for web content
