"""Shared skill discovery utilities.

Provides a single source of truth for skill path resolution, name extraction,
discovery, and relevance scoring across both folder-per-skill and legacy
flat-file formats.
"""
from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import TypedDict


class SkillInfo(TypedDict):
    """Metadata for a discovered skill."""
    name: str
    description: str
    category: str
    file: str


class SkillInfoExtended(TypedDict, total=False):
    """Extended metadata including keywords, when triggers, and full content."""
    name: str
    description: str
    category: str
    file: str
    keywords: str
    when: str
    content: str


def skill_name_from_path(skill_file: Path) -> str:
    """Resolve skill name from path: folder-per-skill → parent dir, legacy → stem.

    This is the canonical name extraction used by both tools/skill.py and
    validate_skills.py.  Do NOT duplicate this logic elsewhere.
    """
    return skill_file.parent.name if skill_file.name == "SKILL.md" else skill_file.stem


def discover_skills(directory: Path) -> list[SkillInfo]:
    """Discover skills in both formats, deduplicated (folder-per-skill wins).

    Returns skills sorted by name.  Emits a warning on collisions.
    """
    if not directory.exists():
        return []

    seen_names: set[str] = set()
    skills: list[SkillInfo] = []

    def _parse(skill_file: Path) -> SkillInfo | None:
        try:
            content = skill_file.read_text(encoding="utf-8")
        except Exception:
            return None

        name = skill_name_from_path(skill_file)
        if name.startswith("_"):
            return None

        desc, cat = name, "general"
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                for line in content[3:end].strip().split("\n"):
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip()
                    elif line.startswith("description:"):
                        desc = line.split(":", 1)[1].strip()
                    elif line.startswith("category:"):
                        cat = line.split(":", 1)[1].strip()
        return {"name": name, "description": desc, "category": cat, "file": str(skill_file)}

    # 1. Folder-per-skill: skills/<name>/SKILL.md
    for skill_file in sorted(directory.glob("*/SKILL.md")):
        info = _parse(skill_file)
        if info and info["name"] not in seen_names:
            seen_names.add(info["name"])
            skills.append(info)

    # 2. Legacy flat files: skills/<name>.md (backward compatibility)
    for md_file in sorted(directory.glob("*.md")):
        if md_file.name.startswith("_"):
            continue
        info = _parse(md_file)
        if info:
            if info["name"] in seen_names:
                warnings.warn(
                    f"Skill '{info['name']}' in {md_file} conflicts with previously discovered skill; "
                    f"ignoring duplicate.",
                    stacklevel=2,
                )
            elif info["name"] not in seen_names:
                seen_names.add(info["name"])
                skills.append(info)

    return skills


def discover_skills_extended(directory: Path) -> list[SkillInfoExtended]:
    """Discover skills with extended metadata (keywords, when triggers, content).

    Returns skills sorted by name.  Includes frontmatter fields 'keywords' and
    the '## When' section text for relevance scoring.
    """
    if not directory.exists():
        return []

    skills: list[SkillInfoExtended] = []

    for d in sorted(directory.iterdir()):
        if not d.is_dir():
            continue
        md = d / "SKILL.md"
        if not md.exists():
            continue
        try:
            content = md.read_text(encoding="utf-8")
        except Exception:
            continue

        info: SkillInfoExtended = {
            "name": d.name,
            "description": "",
            "category": "general",
            "file": str(md),
            "keywords": "",
            "when": "",
            "content": content,
        }

        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                for line in content[3:end].strip().split("\n"):
                    if line.startswith("name:"):
                        info["name"] = line.split(":", 1)[1].strip()
                    elif line.startswith("description:"):
                        info["description"] = line.split(":", 1)[1].strip().strip("'\"")
                    elif line.startswith("category:"):
                        info["category"] = line.split(":", 1)[1].strip().strip("'\"")
                    elif line.startswith("keywords:"):
                        info["keywords"] = line.split(":", 1)[1].strip().strip("'\"")

        when_match = re.search(r"## When\s*\n(.+?)(?=##|\Z)", content, re.DOTALL)
        if when_match:
            info["when"] = when_match.group(1).strip()

        skills.append(info)

    return skills


def score_skill(skill: SkillInfoExtended, query: str) -> int:
    """Score a skill for relevance to a query string.

    Uses weighted word-set intersection across name, description, keywords,
    when triggers, and category.  Returns a non-negative integer score
    (higher = more relevant).

    Weights (tuned for precision):
    - Name match: 15 per word
    - Keyword match: 10 per word
    - When trigger match: 8 per word
    - Description match: 5 per word
    - Category match: 3 per word
    """
    if not query:
        return 0

    q_words = set(query.lower().split())
    if not q_words:
        return 0

    score = 0

    # Keyword match (highest weight for technical terms)
    kw_words = set(skill.get("keywords", "").lower().split())
    score += sum(10 for w in q_words if w in kw_words)

    # When triggers match
    when_words = set(skill.get("when", "").lower().split())
    score += sum(8 for w in q_words if w in when_words)

    # Description match
    desc_words = set(skill.get("description", "").lower().split())
    score += sum(5 for w in q_words if w in desc_words)

    # Name match
    name_words = set(skill.get("name", "").lower().split())
    score += sum(15 for w in q_words if w in name_words)

    # Category match
    cat_words = set(skill.get("category", "").lower().split())
    score += sum(3 for w in q_words if w in cat_words)

    return score


def suggest_skills(query: str, directory: Path, top: int = 5) -> list[tuple[str, int, str]]:
    """Suggest relevant skills for a query.

    Returns list of (name, score, description_snippet) sorted by score descending.
    Only skills with score > 0 are included.
    """
    skills = discover_skills_extended(directory)
    scored = [(s, score_skill(s, query)) for s in skills]
    scored = [(s, sc) for s, sc in scored if sc > 0]
    scored.sort(key=lambda x: (-x[1], x[0]["name"]))
    return [
        (s["name"], sc, s.get("description", "")[:80])
        for s, sc in scored[:top]
    ]
