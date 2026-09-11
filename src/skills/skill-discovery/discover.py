#!/usr/bin/env python3
"""Skill discovery helper — find relevant skills for any task."""
import sys, os, re, glob
from pathlib import Path

SKILLS_DIR = Path(os.path.expanduser("~/.local/tau/skills"))

def find_skills(query, top=5):
    """Find skills matching query keywords."""
    if not query:
        # List all skills
        for d in sorted(SKILLS_DIR.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                print(f"  {d.name}")
        return
    
    query_lower = query.lower()
    query_words = set(re.findall(r'\w+', query_lower))
    
    scores = []
    for d in sorted(SKILLS_DIR.iterdir()):
        if not d.is_dir() or not (d / "SKILL.md").exists():
            continue
        skill = d.name
        content = (d / "SKILL.md").read_text()
        
        score = 0
        # Name match (highest weight)
        if query_lower in skill.lower():
            score += 50
        for w in query_words:
            if w in skill.lower():
                score += 20
        
        # Description match
        desc = re.search(r'description:.*', content)
        if desc and query_lower in desc.group().lower():
            score += 30
        for w in query_words:
            if w in (desc.group().lower() if desc else ''):
                score += 10
        
        # Keyword match
        kw = re.search(r'keywords:.*', content)
        if kw and query_lower in kw.group().lower():
            score += 20
        for w in query_words:
            if w in (kw.group().lower() if kw else ''):
                score += 5
        
        if score > 0:
            scores.append((score, skill))
    
    scores.sort(reverse=True)
    for score, skill in scores[:top]:
        print(f"  {score:3}  {skill}")

if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    find_skills(query)
