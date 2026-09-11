#!/usr/bin/env python3
"""Manifest helper — generate manifest templates."""

from datetime import datetime as dt


def generate_manifest_template(
    goal: str,
    title: str = "",
    success_criteria: str = "",
    subtasks: str = "",
    depth: int = 0,
    parent: str = "",
) -> str:
    """Generate a manifest markdown template."""
    manifest_id = f"manifest-{dt.now().strftime('%Y%m%d%H%M%S')}"
    if not title:
        title = manifest_id

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
        "",
        f"# {title}",
        "",
        "## Goal",
        goal,
        "",
        "## Success Criteria",
    ]

    if success_criteria:
        for line in success_criteria.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("- ["):
                lines.append(line)
            else:
                lines.append(f"- [ ] {line}")
    else:
        lines.append("(none specified)")

    lines += ["", "## Subtasks"]
    if subtasks:
        for line in subtasks.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("- ["):
                lines.append(line)
            else:
                lines.append(f"- [ ] {line}")
    else:
        lines.append("(none specified)")

    lines += ["", "## Progress", "(empty)"]
    return "\n".join(lines)


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Generate a manifest template")
    parser.add_argument("--goal", required=True, help="Goal description")
    parser.add_argument("--title", default="", help="Manifest title")
    parser.add_argument("--criteria", default="", help="Success criteria (newline-separated)")
    parser.add_argument("--subtasks", default="", help="Subtasks (newline-separated)")
    parser.add_argument("--depth", type=int, default=0, help="Depth in hierarchy")
    parser.add_argument("--parent", default="", help="Parent manifest ID")
    parser.add_argument("--output", default="", help="Output file (default: stdout)")
    args = parser.parse_args()

    template = generate_manifest_template(
        goal=args.goal,
        title=args.title,
        success_criteria=args.criteria,
        subtasks=args.subtasks,
        depth=args.depth,
        parent=args.parent,
    )

    if args.output:
        from pathlib import Path
        Path(args.output).write_text(template, encoding="utf-8")
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(template)


if __name__ == "__main__":
    main()
