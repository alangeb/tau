"""Shared manifest utilities for manifest tools and orchestrate.

Centralizes frontmatter parsing, manifest directory resolution, and
manifest loading to eliminate duplication across manifest_create,
manifest_tree, manifest_update, and orchestrate tools.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime as dt
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

__all__ = [
    "FRONTMATTER_RE",
    "parse_frontmatter",
    "manifests_dir",
    "generate_manifest_id",
    "ManifestEntry",
    "load_manifests",
    "read_manifest_frontmatter",
]

# ── Frontmatter parsing ───────────────────────────────────────────

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Extract key: value pairs from YAML frontmatter.

    Handles quoted values and strips whitespace. Returns empty dict
    if no frontmatter is found.
    """
    m = FRONTMATTER_RE.search(text)
    if not m:
        return {}
    result: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            result[k.strip()] = v.strip().strip('"').strip("'")
    return result


# ── Manifest directory ────────────────────────────────────────────

def manifests_dir() -> Path:
    """Return the .tau/manifests/ directory, creating it if needed."""
    base = Path(".tau/manifests")
    base.mkdir(parents=True, exist_ok=True)
    return base


def generate_manifest_id() -> str:
    """Generate a manifest ID with timestamp."""
    return f"manifest-{dt.now().strftime('%Y%m%d%H%M%S')}"


# ── Manifest entry ────────────────────────────────────────────────

@dataclass
class ManifestEntry:
    """Parsed manifest metadata from frontmatter."""
    filename: str
    path: Path
    id: str
    title: str
    goal: str = ""
    status: str = "planning"
    depth: int = 0
    parent: str = ""
    created: str = ""


# ── Manifest loading ──────────────────────────────────────────────

def read_manifest_frontmatter(path: Path) -> dict[str, str] | None:
    """Read and parse frontmatter from a manifest file.

    Returns None if file cannot be read.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return parse_frontmatter(content)


def load_manifests(directory: Path | None = None) -> list[ManifestEntry]:
    """Read all manifest-*.md files and return parsed entries.

    Uses .tau/manifests/ if directory is None.
    """
    if directory is None:
        directory = manifests_dir()
    entries: list[ManifestEntry] = []
    for fp in sorted(directory.glob("manifest-*.md")):
        fm = read_manifest_frontmatter(fp)
        if fm is None:
            continue
        depth_val = fm.get("depth", "0") or "0"
        try:
            depth = int(depth_val)
        except (ValueError, TypeError):
            depth = 0
        entries.append(ManifestEntry(
            filename=fp.name,
            path=fp,
            id=fm.get("id", ""),
            title=fm.get("title", ""),
            goal=fm.get("goal", ""),
            status=fm.get("status", ""),
            depth=depth,
            parent=fm.get("parent", ""),
            created=fm.get("created", ""),
        ))
    return entries
