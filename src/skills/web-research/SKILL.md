---
name: web-research
description: "Web research — search, lookup, fetch, crawl. Find information online, web scraping, article extraction, duckduckgo, mojeek (also load: agent-browser, graphify, image)"
category: research
keywords: web, search, lookup, research, find, browse, google, facts, duckduckgo, wikipedia, extract, scrape, content
---

# Web Research

## When
"search web", "look up", "research topic", "find information", "web search", "browse", "google", "find facts", "search the internet", "duckduckgo", "wikipedia", "extract content", "scrape page"

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

## Helper
```bash
python3 skills/web-research/research_helper.py
```

## Related Skills
- `image` — image loading and vision models
- `agent-browser` — browser automation for interactive research
- `graphify` — build knowledge graphs from research
