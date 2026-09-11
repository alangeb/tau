#!/usr/bin/env python3
"""skill_health.py — Dashboard of skill health metrics.

Usage:
    python3 skills/tauskillmaintenance/skill_health.py [--brief|--verbose|--json]
"""
import sys, os, re, glob, json
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent

def parse_skill(path):
    """Parse skill frontmatter and content."""
    with open(path, errors='ignore') as f:
        content = f.read()
    
    if not content.startswith('---'):
        return None
    
    frontmatter = content.split('---', 2)[1]
    body = content.split('---', 2)[2] if content.count('---') >= 2 else ''
    
    data = {'path': path, 'size': len(content), 'lines': content.count('\n')}
    
    for line in frontmatter.split('\n'):
        if ':' in line:
            key, _, val = line.partition(':')
            data[key.strip()] = val.strip().strip('"')
    
    data['body'] = body
    return data

def compute_findability(skill):
    """Compute findability score (0-100)."""
    score = 0
    desc = skill.get('description', '')
    keywords = skill.get('keywords', '')
    body = skill.get('body', '')
    
    # Description quality (30-200 chars = +25)
    if 30 <= len(desc) <= 200:
        score += 25
    
    # Keywords (5-15 = +25)
    kw_count = len([k for k in keywords.split(',') if k.strip()])
    if 5 <= kw_count <= 15:
        score += 25
    
    # Cross-references (3-10 = +20)
    m = re.search(r'\(also load:\s*(.*?)\)', desc)
    if m:
        ref_count = len([r for r in m.group(1).split(',') if r.strip()])
        if 3 <= ref_count <= 10:
            score += 20
    
    # Helper exists (+10)
    skill_name = skill.get('name', '')
    helpers = glob.glob(f"{SKILLS_DIR}/{skill_name}/*.py") + glob.glob(f"{SKILLS_DIR}/{skill_name}/*.sh")
    if helpers:
        score += 10
    
    # Lines < 80 (+20)
    if skill.get('lines', 100) < 80:
        score += 10
    
    return score

def main():
    brief = '--brief' in sys.argv
    verbose = '--verbose' in sys.argv
    as_json = '--json' in sys.argv
    
    skills = []
    for path in sorted(glob.glob(f'{SKILLS_DIR}/*/SKILL.md')):
        skill = parse_skill(path)
        if skill:
            skill['findability'] = compute_findability(skill)
            skills.append(skill)
    
    if as_json:
        print(json.dumps(skills, indent=2))
        return
    
    # Summary stats
    scores = [s['findability'] for s in skills]
    avg = sum(scores) / len(scores) if scores else 0
    healthy = sum(1 for s in scores if s >= 70)
    critical = sum(1 for s in scores if s < 50)
    
    print(f"Skill Health Dashboard")
    print(f"{'='*50}")
    print(f"Total skills: {len(skills)}")
    print(f"Avg findability: {avg:.0f}/100")
    print(f"Healthy (≥70): {healthy} | Critical (<50): {critical}")
    print()
    
    if not brief:
        # Show critical skills
        critical_skills = [s for s in skills if s['findability'] < 50]
        if critical_skills:
            print(f"Critical skills (<50 findability):")
            for s in sorted(critical_skills, key=lambda x: x['findability']):
                print(f"  {s['name']:30s} score={s['findability']:3d}  size={s['size']}B  lines={s['lines']}")
            print()
        
        # Show top skills
        print(f"Top 10 skills:")
        for s in sorted(skills, key=lambda x: -x['findability'])[:10]:
            status = '✓' if s['findability'] >= 70 else '⚠' if s['findability'] >= 50 else '✗'
            print(f"  {status} {s['name']:30s} score={s['findability']:3d}  size={s['size']}B  lines={s['lines']}")
    
    if verbose:
        print()
        print("All skills:")
        for s in sorted(skills, key=lambda x: -x['findability']):
            status = '✓' if s['findability'] >= 70 else '⚠' if s['findability'] >= 50 else '✗'
            helpers = len(glob.glob(f"{SKILLS_DIR}/{s.get('name','')}/*.py")) + len(glob.glob(f"{SKILLS_DIR}/{s.get('name','')}/*.sh"))
            print(f"  {status} {s['name']:30s} score={s['findability']:3d}  helpers={helpers}  size={s['size']}B")

if __name__ == '__main__':
    main()
