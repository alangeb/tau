"""Manifest create tool — create manifest files for goal-driven delegation."""

from __future__ import annotations

from tools import ToolContext, ToolMetadata
from tools.lib.manifest import generate_manifest_id, manifests_dir

from dataclasses import dataclass
from datetime import datetime as dt
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_core import TauErgon

__all__ = ["Args", "run"]

# ── Tool metadata ─────────────────────────────────────────────────

metadata = ToolMetadata(
    name="manifest_create",
    description=(
        "Create a manifest file for goal-driven delegation. "
        "Manifests track goals, success criteria, subtasks, and progress. "
        "Returns manifest path."
    ),
    max_size=16384,
)

# ── Args schema ───────────────────────────────────────────────────

@dataclass
class Args:
    goal: str
    title: str = ""
    success_criteria: str = ""
    subtasks: str = ""
    depth: int = 0
    parent: str = ""


# ── Helpers ───────────────────────────────────────────────────────

def _parse_lines(raw: str) -> list[str]:
    """Split a newline-separated string into non-empty lines."""
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _format_frontmatter(manifest_id: str, title: str, goal: str, depth: int, parent: str | None) -> str:
    """Build the YAML frontmatter block."""
    lines = [
        "---",
        f'id: "{manifest_id}"',
        f'title: "{title}"',
        f'goal: "{goal}"',
        'status: "planning"',
        f"depth: {depth}",
        f"parent: {parent if parent else 'null'}",
        f'created: "{dt.now().isoformat()}"',
        "---",
    ]
    return "\n".join(lines)


def _format_success_criteria(criteria: list[str]) -> str:
    """Format success criteria as a markdown checklist."""
    if not criteria:
        return "(none specified)"
    lines = []
    for i, c in enumerate(criteria, 1):
        # If already formatted as a checkbox, use as-is
        if c.strip().startswith("- ["):
            lines.append(c.strip())
        else:
            lines.append(f"- [ ] {i}. {c} → Verify: `command`")
    return "\n".join(lines)


def _format_subtasks(subtasks: list[str]) -> str:
    """Format subtasks as a markdown checklist."""
    if not subtasks:
        return "(none specified)"
    lines = []
    for i, s in enumerate(subtasks, 1):
        # If already formatted as a checkbox, use as-is
        if s.strip().startswith("- ["):
            lines.append(s.strip())
        else:
            lines.append(f"- [ ] {i}. {s}")
    return "\n".join(lines)


def _build_manifest(
    manifest_id: str,
    title: str,
    goal: str,
    depth: int,
    parent: str | None,
    criteria: list[str],
    subtasks: list[str],
) -> str:
    """Assemble the full manifest markdown content."""
    sections = [
        _format_frontmatter(manifest_id, title, goal, depth, parent),
        "",
        f"# Manifest: {title}",
        "",
        "## Goal",
        goal,
        "",
        "## Success Criteria",
        _format_success_criteria(criteria),
        "",
        "## Subtasks",
        _format_subtasks(subtasks),
        "",
        "## Progress",
        "(empty)",
    ]
    return "\n".join(sections)


# ── Run ───────────────────────────────────────────────────────────

def run(
    goal: str,
    title: str = "",
    success_criteria: str = "",
    subtasks: str = "",
    depth: int = 0,
    parent: str = "",
    _ctx: ToolContext | None = None,
) -> str:
    """Create a manifest file and return its path."""
    agent = _ctx.agent if _ctx else None
    tool_call_id = _ctx.tool_call_id if _ctx else None

    # Generate ID and filename
    manifest_id = generate_manifest_id()
    manifest_file = manifests_dir() / f"{manifest_id}.md"

    # Parse inputs
    title = title or manifest_id
    criteria = _parse_lines(success_criteria)
    task_list = _parse_lines(subtasks)
    parent_path = parent if parent else None

    # Build and write manifest
    content = _build_manifest(
        manifest_id=manifest_id,
        title=title,
        goal=goal,
        depth=depth,
        parent=parent_path,
        criteria=criteria,
        subtasks=task_list,
    )

    manifest_file.write_text(content + "\n", encoding="utf-8")

    return str(manifest_file)
