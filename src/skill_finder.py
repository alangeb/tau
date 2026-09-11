#!/usr/bin/env python3
"""skill_finder.py — Find relevant skills for a task description.
Usage: python3 skill_finder.py <query> [top=N]
Scores skills by keyword match + description relevance. Outputs ranked list.
"""
import sys
from pathlib import Path

# Ensure src/ is on the path for lib.skill_discovery import
_src = Path(__file__).resolve().parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from lib.skill_discovery import suggest_skills


def main() -> int:
    skills_dir = Path(__file__).parent / "skills"

    if len(sys.argv) < 2:
        print("Usage: python3 skill_finder.py <query> [top=N]")
        sys.exit(1)

    # Parse args: last arg is top=N if it's a digit, otherwise part of query
    args = sys.argv[1:]
    top = 10
    if args[-1].isdigit():
        top = int(args[-1])
        args = args[:-1]

    query = " ".join(args)

    results = suggest_skills(query, skills_dir, top=top)

    if not results:
        print(f"No skills found for: {query}")
        return 0

    for name, sc, desc in results:
        print(f"{sc:3d}  {name:<30} {desc[:80]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
