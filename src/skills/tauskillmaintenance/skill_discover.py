#!/usr/bin/env python3
"""Skill discovery helper — suggest skills based on user prompt or tool usage patterns."""
import sys
from pathlib import Path

# Ensure src/ is on the path for lib.skill_discovery import
_src = Path(__file__).resolve().parent.parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from lib.skill_discovery import suggest_skills


SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: skill_discover.py <query> [top=N]")
        print("Example: skill_discover.py 'debug python crash'")
        sys.exit(1)

    args = sys.argv[1:]
    top = 5
    if args[-1].isdigit():
        top = int(args[-1])
        args = args[:-1]

    query = " ".join(args)
    results = suggest_skills(query, SKILLS_DIR, top=top)

    if not results:
        print(f"No skills found for: {query}")
        return 0

    for name, sc, desc in results:
        print(f"{sc:3d}  {name:<30} {desc[:80]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
