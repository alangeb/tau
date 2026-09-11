"""Manifest tree tool — show manifest hierarchy as a tree."""

from __future__ import annotations

from tools import ToolContext, ToolMetadata
from tools.lib.manifest import ManifestEntry, load_manifests, manifests_dir

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_core import TauErgon

__all__ = ["Args", "run"]

# ── Tool metadata ──────────────────────────────────────────────────

metadata = ToolMetadata(
    name="manifest_tree",
    description=(
        "Show manifest hierarchy as a tree. Reads manifests from .tau/manifests/, "
        "parses YAML frontmatter, and renders the parent-child tree with status icons."
    ),
    max_size=16384,
)

# ── Args schema ────────────────────────────────────────────────────

@dataclass
class Args:
    root: str = ""  # optional root manifest path to filter subtree

# ── Status icons ───────────────────────────────────────────────────

_STATUS_ICONS = {
    "complete": "✓",
    "failed": "✗",
    "executing": "⟳",
    "planning": "○",
}

# ── Tree building ──────────────────────────────────────────────────


def _build_children(entries: list[ManifestEntry]) -> dict[str, list[ManifestEntry]]:
    """Map each manifest id to its list of children."""
    children: dict[str, list[ManifestEntry]] = {}
    for e in entries:
        parent = e.parent
        if parent:
            children.setdefault(parent, []).append(e)
    return children


def _find_roots(entries: list[ManifestEntry]) -> list[ManifestEntry]:
    """Return manifests that have no parent."""
    return [e for e in entries if not e.parent or e.parent == "null"]


def _subtree_roots(entries: list[ManifestEntry], root_id: str) -> list[ManifestEntry]:
    """Return manifests whose root ancestor is *root_id*."""
    children = _build_children(entries)
    roots = [e for e in entries if e.id == root_id]
    if roots:
        return roots
    # Maybe root_id is a filename, not an id
    roots = [e for e in entries if e.filename == root_id]
    return roots

# ── Tree rendering ─────────────────────────────────────────────────


def _render_tree(
    nodes: list[ManifestEntry],
    children_map: dict[str, list[ManifestEntry]],
    prefix: str = "",
) -> str:
    """Recursively render a manifest tree."""
    lines: list[str] = []
    total = len(nodes)

    for idx, node in enumerate(nodes):
        is_last_node = idx == total - 1
        connector = "└── " if is_last_node else "├── "

        status_icon = _STATUS_ICONS.get(node.status, "?")
        status_label = f"[{node.status}]" if node.status else "[?]"
        depth = node.depth

        label = f"{node.filename} {status_label} {status_icon} (depth {depth})"
        lines.append(f"{prefix}{connector}{label}" if prefix else label)

        # Recurse into children keyed by id
        child_nodes = children_map.get(node.id, [])
        if child_nodes:
            child_prefix = prefix + ("    " if is_last_node else "│   ")
            lines.append(_render_tree(child_nodes, children_map, child_prefix))

    return "\n".join(lines)

# ── Public entry point ─────────────────────────────────────────────


def run(
    _ctx: ToolContext | None = None,
    args: Args | None = None,
) -> str:
    root_filter = (args.root if args else "") or ""

    mdir = manifests_dir()
    entries = load_manifests(mdir)
    if not entries:
        return "No manifests found in .tau/manifests/"

    children_map = _build_children(entries)

    if root_filter:
        nodes = _subtree_roots(entries, root_filter)
        if not nodes:
            return f"No manifest found matching root: {root_filter}"
    else:
        nodes = _find_roots(entries)

    return _render_tree(nodes, children_map)
