#!/usr/bin/env python3
"""skill_crossref.py — Verify bidirectional cross-references between skills."""
import sys, re, os
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent

def parse_skill(skill_dir):
    """Extract also_load and related_skills from a SKILL.md."""
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return None
    name = skill_dir.name
    text = md.read_text()
    # Parse "also load:" from description line
    also_load = set()
    m = re.search(r'also\s+load:\s*(.+?)(?:\)|$)', text, re.IGNORECASE)
    if m:
        also_load = {s.strip() for s in m.group(1).split(',') if s.strip()}
    # Parse "Related Skills" section
    related = set()
    rel_match = re.search(r'##\s*Related Skills\s*\n(.*?)(?=\n##|\Z)', text, re.DOTALL | re.IGNORECASE)
    if rel_match:
        for line in rel_match.group(1).splitlines():
            # Match `name` or **name** or plain name
            m2 = re.match(r'-\s+`([^`]+)`', line) or re.match(r'-\s+\*\*(\S+)\*\*', line) or re.match(r'-\s+(\S+)', line)
            if m2:
                related.add(m2.group(1))
    return {"name": name, "also_load": also_load, "related": related}

def main():
    if "--help" in sys.argv:
        print("Usage: skill_crossref.py [--check] [--verbose]")
        print("  Verify bidirectional cross-references between skills.")
        print("  --check   Exit non-zero if one-way refs found")
        print("  --verbose Show all references, not just one-way")
        sys.exit(0)
    check_exit = "--check" in sys.argv
    verbose = "--verbose" in sys.argv
    skills = {}
    for d in sorted(SKILLS_DIR.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            info = parse_skill(d)
            if info:
                skills[info["name"]] = info
    # Build all known skill names
    known = set(skills.keys())
    # Check for broken references (referencing non-existent skills)
    broken = []
    for name, info in sorted(skills.items()):
        all_refs = info["also_load"] | info["related"]
        for ref in sorted(all_refs):
            if ref not in known:
                broken.append((name, ref))
    # Check bidirectionality
    one_way = []
    for name, info in sorted(skills.items()):
        all_refs = info["also_load"] | info["related"]
        for ref in sorted(all_refs):
            if ref not in known:
                continue
            target = skills[ref]
            target_refs = target["also_load"] | target["related"]
            if name not in target_refs:
                one_way.append((name, ref))
    # Report
    if broken:
        print(f"BROKEN REFERENCES ({len(broken)}):")
        for src, tgt in broken:
            print(f"  {src} -> {tgt} (does not exist)")
    if one_way:
        print(f"ONE-WAY REFERENCES ({len(one_way)}):")
        for src, tgt in one_way:
            print(f"  {src} -> {tgt} (not reciprocated)")
    if verbose:
        print(f"\nALL REFERENCES:")
        for name, info in sorted(skills.items()):
            all_refs = info["also_load"] | info["related"]
            if all_refs:
                print(f"  {name} -> {', '.join(sorted(all_refs))}")
    if not broken and not one_way:
        print("All cross-references are valid and bidirectional.")
    if check_exit and (broken or one_way):
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
