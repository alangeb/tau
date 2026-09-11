#!/usr/bin/env python3
"""Skill finder — search and list available skills."""
import os
import sys
import re

SKILLS_DIR = os.path.expanduser("~/.local/tau/skills")

def list_skills():
    """List all available skills."""
    skills = []
    for d in sorted(os.listdir(SKILLS_DIR)):
        path = os.path.join(SKILLS_DIR, d, "SKILL.md")
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
                m = re.search(r'^name:\s*(.+)', content, re.MULTILINE)
                name = m.group(1).strip() if m else d
                m = re.search(r'^description:\s*(.+)', content, re.MULTILINE)
                desc = m.group(1).strip() if m else ""
                skills.append({"name": name, "dir": d, "description": desc})
    return skills

def search_skills(query):
    """Search skills by keyword."""
    results = []
    query_lower = query.lower()
    for skill in list_skills():
        if query_lower in skill["name"].lower() or query_lower in skill["description"].lower():
            results.append(skill)
    return results

def get_skill(name):
    """Get skill content by name."""
    path = os.path.join(SKILLS_DIR, name, "SKILL.md")
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        for skill in list_skills():
            print(f"{skill['name']:30} {skill['description'][:60]}...")
        sys.exit(0)
    action = sys.argv[1]
    if action == "search" and len(sys.argv) > 2:
        for skill in search_skills(sys.argv[2]):
            print(f"{skill['name']}: {skill['description'][:80]}")
    elif action == "get" and len(sys.argv) > 2:
        content = get_skill(sys.argv[2])
        if content:
            print(content)
        else:
            print(f"Skill not found: {sys.argv[2]}")
            sys.exit(1)
    else:
        print(f"Usage: skill_finder.py [search|get] <name>")
        sys.exit(1)
