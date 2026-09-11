#!/usr/bin/env python3
"""skill_overlap.py — Detect keyword overlap between skills using Jaccard similarity."""
import sys, re
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent

def parse_keywords(skill_dir):
    """Extract keywords from SKILL.md."""
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return None
    text = md.read_text()
    m = re.search(r'^keywords:\s*(.+)$', text, re.MULTILINE)
    if not m:
        return None
    raw = [s.strip().lower() for s in m.group(1).split(',')]
    return {s for s in raw if s}

def jaccard(a, b):
    """Compute Jaccard similarity between two sets."""
    if not a and not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0

def main():
    if "--help" in sys.argv:
        print("Usage: skill_overlap.py [--threshold FLOAT] [--matrix]")
        print("  Detect keyword overlap between skills (Jaccard similarity).")
        print("  --threshold N  Overlap threshold (default: 0.6)")
        print("  --matrix       Show full overlap matrix")
        sys.exit(0)
    threshold = 0.6
    show_matrix = "--matrix" in sys.argv
    for i, arg in enumerate(sys.argv):
        if arg == "--threshold" and i + 1 < len(sys.argv):
            threshold = float(sys.argv[i + 1])
    # Parse all skills
    skills = {}
    for d in sorted(SKILLS_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith("_") and (d / "SKILL.md").exists():
            kw = parse_keywords(d)
            if kw:
                skills[d.name] = kw
    # Compute pairwise overlaps
    names = sorted(skills.keys())
    overlaps = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            sim = jaccard(skills[a], skills[b])
            overlaps.append((sim, a, b))
    overlaps.sort(reverse=True)
    # Report high overlaps
    flagged = [(s, a, b) for s, a, b in overlaps if s >= threshold]
    if flagged:
        print(f"HIGH OVERLAP pairs (>= {threshold:.0%} Jaccard):")
        for sim, a, b in flagged:
            shared = skills[a] & skills[b]
            print(f"  {a} <-> {b}: {sim:.1%} (shared: {', '.join(sorted(shared))})")
    else:
        print(f"No pairs with >= {threshold:.0%} Jaccard overlap.")
    if show_matrix:
        print(f"\nFULL OVERLAP MATRIX (top 10):")
        for sim, a, b in overlaps[:10]:
            print(f"  {a:30s} <-> {b:30s}: {sim:.1%}")
        print(f"  ... ({len(overlaps)} total pairs)")
    sys.exit(0)

if __name__ == "__main__":
    main()
