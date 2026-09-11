---
category: research
description: "Search web, find information, scrape website, article extraction, duckduckgo — use search, lookup, fetch, crawl tools for deep research (also load: agent-browser, grep_tool, shell_scripting, image, wiki)"
keywords: web research, web search, information search, website scraping, article extraction, duckduckgo, web content
name: web-research
---

# Web Research

## When
"search web", "look up", "research topic", "find information", "web search", "browse", "google", "find facts"

## Tools
```
search(query="...")              # DuckDuckGo search
lookup(query="...")             # Wikipedia/DDG instant answer
fetch(url="...")                 # Extract page content
crawl(url="...", depth=2)        # Multi-page crawl
```

## Patterns
- **Fact lookup**: `lookup` — fast, structured
- **Deep research**: `search` → `fetch` → `crawl`
- **Interactive**: `agent-browser` for JS-heavy sites
- **Batch**: `search` → extract URLs → `fetch` multiple

## Tau-Specific Patterns
- Research tau issues: `search(query="tau ergon", timelimit="m")`
- Fetch design docs: `fetch(url="...")` for remote content
- Batch: `search` → extract URLs → `fetch(url="url1,url2")`

## Helper
```bash
python3 skills/web-research/research_helper.py
```

## Related Skills
- `data_processing` — Structured data processing
- `image` — image loading and vision models
- `agent-browser` — browser automation for interactive research
- `graphify` — build knowledge graphs from research
- `wiki` — knowledge storage and retrieval
- `signal-cli` — signal-cli web research
