"""Wiki tool — configuration, search, and content operations."""

from __future__ import annotations

from tools import ToolContext, ToolMetadata

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from agent_core import TauErgon

# ── Tool metadata ──

metadata = ToolMetadata(
    name="wiki",
    description=(
        "Manage wiki. Get/set path, check status, search content, "
        "add entries, or retrieve entries. Wiki path stored in tau.json."
    ),
    max_size=16384,
    timeout=30,
)


# ── Args schema ──

@dataclass
class Args:
    """Wiki tool arguments."""
    mode: Literal["get", "set", "status", "search", "add", "retrieve"] = field(
        default="get",
        metadata={"description": "Operation: get/set path, status, search, add entry, retrieve entry"},
    )
    path: str = field(default="", metadata={"description": "Path for 'set' mode"})
    query: str = field(default="", metadata={"description": "Search query or entry topic"})
    content: str = field(default="", metadata={"description": "Content for 'add' mode"})
    type: str = field(default="session", metadata={"description": "Entry type: session/query/decision/reference/playbook"})
    topic: str = field(default="", metadata={"description": "Topic folder for 'add' mode"})


# ── Helpers ──

def _get_tau_json_path() -> Path:
    """Return path to tau.json."""
    import sys
    script = Path(sys.argv[0]).resolve()
    return script.parent / "tau.json" if script.exists() else Path.cwd() / "tau.json"


def _load_tau_json() -> dict:
    """Load tau.json, return {} if missing."""
    tau_json = _get_tau_json_path()
    if not tau_json.exists():
        return {}
    try:
        return json.loads(tau_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_tau_json(data: dict) -> None:
    """Save data to tau.json."""
    tau_json = _get_tau_json_path()
    tau_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _git_run(wiki_dir: Path, args: list[str]) -> str:
    """Run git command in wiki directory."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, timeout=5,
            start_new_session=True, cwd=str(wiki_dir),
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def _count_files(wiki_dir: Path) -> int:
    """Count markdown files in wiki directory."""
    count = 0
    for root, dirs, files in os.walk(wiki_dir):
        count += sum(1 for f in files if f.endswith(".md"))
    return count


def _total_size(wiki_dir: Path) -> int:
    """Total size of wiki directory in bytes."""
    total = 0
    for root, dirs, files in os.walk(wiki_dir):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return total


def _get_wiki_dir() -> Path:
    """Return wiki directory from config."""
    from agent_config import get_config
    cfg = get_config()
    return Path(cfg.wiki.path).resolve()


# ── Execution ──

def run(
    mode: Literal["get", "set", "status", "search", "add", "retrieve"] = "get",
    path: str = "",
    query: str = "",
    content: str = "",
    type: str = "session",
    topic: str = "",
    _ctx: ToolContext | None = None,
) -> str:
    """Execute wiki operation."""
    agent = _ctx.agent if _ctx else None
    tool_call_id = _ctx.tool_call_id if _ctx else None

    if mode == "get":
        return _get_wiki_path()
    elif mode == "set":
        return _set_wiki_path(path)
    elif mode == "status":
        return _wiki_status()
    elif mode == "search":
        return _wiki_search(query)
    elif mode == "add":
        return _wiki_add(query, content, type, topic)
    elif mode == "retrieve":
        return _wiki_retrieve(query)
    else:
        return f"ERROR: Unknown mode '{mode}'. Use 'get', 'set', 'status', 'search', 'add', or 'retrieve'."


def _get_wiki_path() -> str:
    """Return current wiki path from config."""
    try:
        from agent_config import get_config
        cfg = get_config()
        wiki_path = cfg.wiki.path
        return f"Wiki path: {wiki_path}"
    except Exception as e:
        return f"ERROR: Cannot get wiki path: {e}"


def _set_wiki_path(new_path: str) -> str:
    """Update wiki path in tau.json."""
    if not new_path:
        return "ERROR: Path is required for set mode. Usage: wiki set path=/path/to/wiki"

    # Expand path
    resolved = os.path.expanduser(new_path)
    resolved_path = Path(resolved).resolve()

    # Check if path exists or create it
    if not resolved_path.exists():
        try:
            resolved_path.mkdir(parents=True, exist_ok=True)
            created = True
        except OSError as e:
            return f"ERROR: Cannot create wiki directory: {e}"
    else:
        created = False

    # Update tau.json
    try:
        tau_data = _load_tau_json()
        tau_data.setdefault("wiki", {})["path"] = str(resolved_path)
        _save_tau_json(tau_data)

        # Force config reload
        from agent_config import reset_config_cache
        reset_config_cache()

        result = f"Wiki path updated to: {resolved_path}"
        if created:
            result += " (directory created)"
        return result
    except Exception as e:
        return f"ERROR: Cannot update tau.json: {e}"


def _wiki_status() -> str:
    """Check wiki status."""
    try:
        wiki_dir = _get_wiki_dir()

        lines = [f"Wiki path: {wiki_dir}"]

        # Check exists
        exists = wiki_dir.exists()
        lines.append(f"Exists: {exists}")

        if not exists:
            lines.append("Wiki directory does not exist. Use 'wiki set' to create it.")
            return "\n".join(lines)

        # File count
        file_count = _count_files(wiki_dir)
        lines.append(f"Markdown files: {file_count}")

        # Total size
        total = _total_size(wiki_dir)
        if total > 1024 * 1024:
            lines.append(f"Total size: {total / (1024 * 1024):.2f} MB")
        else:
            lines.append(f"Total size: {total / 1024:.1f} KB")

        # Git status
        git_status = _git_run(wiki_dir, ["status", "--short"])
        if git_status:
            lines.append(f"Git: {len(git_status.splitlines())} uncommitted changes")
        else:
            lines.append("Git: clean")

        # Git log
        git_log = _git_run(wiki_dir, ["log", "--oneline", "-1"])
        if git_log:
            lines.append(f"Last commit: {git_log}")

        return "\n".join(lines)
    except Exception as e:
        return f"ERROR: Cannot check wiki status: {e}"


def _wiki_search(query: str) -> str:
    """Search wiki content."""
    if not query:
        return "ERROR: Query is required for search mode. Usage: wiki search query='keyword'"

    try:
        wiki_dir = _get_wiki_dir()

        if not wiki_dir.exists():
            return "ERROR: Wiki directory does not exist."

        # Search INDEX.md first
        index_file = wiki_dir / "INDEX.md"
        if index_file.exists():
            index_content = index_file.read_text(encoding="utf-8")
            matches = [line for line in index_content.splitlines() if query.lower() in line.lower()]
            if matches:
                return f"INDEX matches ({len(matches)}):\n" + "\n".join(matches[:20])

        # Grep all .md files
        result = subprocess.run(
            ["grep", "-ri", query, "--include=*.md", str(wiki_dir)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            matches = result.stdout.strip().splitlines()[:30]
            return f"Grep matches ({len(matches)}):\n" + "\n".join(matches)
        else:
            return f"No matches found for '{query}'"
    except Exception as e:
        return f"ERROR: Search failed: {e}"


def _wiki_add(topic: str, content: str, type: str = "session", query: str = "") -> str:
    """Add wiki entry."""
    if not topic:
        return "ERROR: Topic is required for add mode. Usage: wiki add topic='topic' content='...'"

    try:
        wiki_dir = _get_wiki_dir()

        if not wiki_dir.exists():
            return "ERROR: Wiki directory does not exist."

        # Create topic folder if needed
        topic_dir = wiki_dir / topic
        topic_dir.mkdir(parents=True, exist_ok=True)

        # Create entry file
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        entry_file = topic_dir / f"{topic}-{date_str}.md"

        # Write content
        frontmatter = f"---\ntype: {type}\ntitle: {query or topic}\ncreated: {date_str}\nupdated: {date_str}\n---\n\n"
        entry_file.write_text(frontmatter + content, encoding="utf-8")

        return f"Added: {entry_file}"
    except Exception as e:
        return f"ERROR: Add failed: {e}"


def _wiki_retrieve(query: str) -> str:
    """Retrieve wiki entry by topic."""
    if not query:
        return "ERROR: Query is required for retrieve mode. Usage: wiki retrieve query='topic'"

    try:
        wiki_dir = _get_wiki_dir()

        if not wiki_dir.exists():
            return "ERROR: Wiki directory does not exist."

        # Try topic folder
        topic_dir = wiki_dir / query
        if topic_dir.exists() and topic_dir.is_dir():
            # Find latest entry
            entries = sorted(topic_dir.glob("*.md"))
            if entries:
                latest = entries[-1]
                return f"Latest entry: {latest}\n\n{latest.read_text(encoding='utf-8')[:4000]}"
            else:
                return f"Topic '{query}' exists but has no entries."

        # Try exact file match
        for root, dirs, files in os.walk(wiki_dir):
            for f in files:
                if f.startswith(query) and f.endswith(".md"):
                    entry_file = Path(root) / f
                    return f"Found: {entry_file}\n\n{entry_file.read_text(encoding='utf-8')[:4000]}"

        return f"No entries found for '{query}'"
    except Exception as e:
        return f"ERROR: Retrieve failed: {e}"