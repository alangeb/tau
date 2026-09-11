---
category: analysis
description: "Visualize codebases as knowledge graphs and diagrams — AST graph, community detection, path queries (also load: pyprep, review, spec)"
keywords: AST knowledge graph, community detection algorithm, shortest path query, graph traversal, cohesion scoring, node explanation
name: graphify
---

# Graphify

## When
"codebase graph" "knowledge graph" "graphify" "code architecture" "file relationships" "project analysis" "python analysis" "code review" "review code"

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
2. **Detect**: `graphify.detect.detect(Path('INPUT_PATH'))` → `.graphify_detect.json`. `total_files=0` → stop. `>2M words` or `>500 files` → narrow scope.
3. **Extract** (parallel AST + semantic):
   - AST: `graphify.extract.extract(code_files)` → `.graphify_ast.json`.
   - Semantic: Subagent dispatch (5-10x faster). Split 20-25/chunk. Prompt: `references/extraction-spec.md`.
   - Merge → `.graphify_extract.json`.
4. **Build**: `build_from_json(extraction, directed=True)` → cluster, score → `graph.json`, `GRAPH_REPORT.md`.
5. **Label**: 2-5 word community names → `.graphify_labels.json`.
6. **Export**: `graphify export html` (default). See `references/exports.md`.
7. **Cleanup**: Remove temp files. Report outputs.

## Flags
`--mode deep` (richer edges) | `--update` (incremental) | `--directed` (preserve direction) | `--no-viz` (skip HTML) | `--svg --graphml --neo4j --mcp` (exports) | `--obsidian` (vault) | `--watch --wiki` (auto-rebuild)

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

## Helper
```bash
python3 skills/graphify/pipeline.py <path> [flags...]  # Run full graph pipeline
graphify query "<question>"                          # Query existing graph
graphify path "A" "B"                               # Shortest path
graphify explain "Node"                              # Plain explanation
```

## Related Skills
- `bug_investigation` — graph-based bug analysis
- `code-review-workflow` — uses pyscan/pygraph for Python projects (sibling)
- `web-research` — graphify for web content
- `wiki` — knowledge storage and retrieval
- `dependency_management` — knowledge graph analysis
- `spec` — System design, ADR, component diagrams
