---
name: web-research
description: Web research — search, lookup, fetch, crawl. Search web, look up, research, find information, browse, google, find facts, duckduckgo, wikipedia, extract content (also load: agent-browser, graphify, image)
category: research
keywords: web, search, lookup, research, find, browse, google, facts, duckduckgo, wikipedia, extract, scrape, content
---

# Web Research

## When
"search web", "look up", "research topic", "find information", "web search", "browse", "google", "find facts", "search the internet", "duckduckgo", "wikipedia", "extract content", "scrape page"

## Tool Sequence
```
search(query="...")              # DuckDuckGo search
lookup(query="...")             # Wikipedia/DDG instant answer
fetch(url="...")                 # Extract page content
crawl(url="...", depth=2)        # Multi-page crawl
```

## Patterns
- **Fact lookup**: `lookup` → fast, structured results
- **Deep research**: `search` → `fetch` → `crawl`
- **Browser automation**: `agent-browser` for interactive tasks
- **Batch research**: `search` → extract URLs → `fetch` multiple

## Helper

```bash
python3 skills/web-research/research_helper.py  # web research helper
```
## Related Skills
- `image` — image loading and vision models
- `agent-browser` — browser automation for interactive research
- `shell_scripting` — automate research workflows
- `tau_audit` — analyze research patterns
- `graphify` — build knowledge graphs from research
