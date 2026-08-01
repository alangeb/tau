#!/usr/bin/env python3
"""Web research helper — batch search, fetch, and research workflow utilities."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

TAU = str(Path.home() / "tau" / "tau.py")


def research_plan(topic: str) -> list[str]:
    """Generate search queries for comprehensive topic research."""
    return [
        topic,
        f"{topic} tutorial",
        f"{topic} best practices",
        f"{topic} examples",
        f"{topic} documentation",
        f"{topic} vs alternatives",
    ]


def batch_search_queries(queries: list[str], limit: int = 5) -> list[dict]:
    """Build structured search tool calls for batch execution."""
    return [{"tool": "search", "args": {"query": q, "limit": limit}} for q in queries]


def _run_tau_tool(tool: str, **kwargs) -> str:
    """Run a tau.py tool call and return stdout."""
    args = [TAU, f"{tool}("]
    for k, v in kwargs.items():
        args.append(f"{k}={json.dumps(v)}")
    args.append(")")
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    return result.stdout


def search(query: str, limit: int = 5) -> list[dict]:
    """Search the web and return results as list of {title, url, snippet}."""
    output = _run_tau_tool("search", query=query, limit=limit)
    try:
        data = json.loads(output.strip())
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return [{"raw": output.strip()}]


def fetch_url(url: str, max_length: int = 5000) -> str:
    """Fetch and extract content from a URL."""
    return _run_tau_tool("fetch", url=url, max_length=max_length).strip()


def research_topic(topic: str, depth: int = 2) -> dict:
    """Full research workflow: search → fetch top results → summarize.
    
    Returns dict with query, search_results, fetched_content, and summary.
    """
    queries = research_plan(topic)[:depth + 1]
    results = search(queries[0], limit=5)
    
    fetched: list[dict] = []
    for r in results[:depth]:
        url = r.get("url", "")
        if url:
            try:
                content = fetch_url(url, max_length=3000)
                fetched.append({"url": url, "title": r.get("title", ""), "content": content[:2000]})
            except Exception as e:
                fetched.append({"url": url, "error": str(e)})
    
    return {
        "topic": topic,
        "queries": queries,
        "search_results": results,
        "fetched": fetched,
        "total_sources": len(fetched),
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps(research_plan("example topic"), indent=2))
        return
    
    cmd = sys.argv[1]
    if cmd == "plan":
        topic = sys.argv[2] if len(sys.argv) > 2 else "example"
        print(json.dumps(research_plan(topic), indent=2))
    elif cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        print(json.dumps(search(query, limit), indent=2))
    elif cmd == "fetch":
        url = sys.argv[2] if len(sys.argv) > 2 else ""
        max_len = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
        print(fetch_url(url, max_len))
    elif cmd == "research":
        topic = sys.argv[2] if len(sys.argv) > 2 else ""
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 2
        print(json.dumps(research_topic(topic, depth), indent=2, default=str))
    else:
        print(f"Usage: {sys.argv[0]} {{plan|search|fetch|research}} [args...]")
        sys.exit(1)


if __name__ == "__main__":
    main()
