#!/usr/bin/env python3
"""Skill audit script — check quality, cross-references, findability, health, discovery, overlap."""
import os, re, sys, argparse
from collections import Counter

def _parse_skills(skills_dir="skills"):
    """Parse all SKILL.md files and return structured data."""
    skills = {}
    for d in sorted(os.listdir(skills_dir)):
        f = os.path.join(skills_dir, d, "SKILL.md")
        if os.path.exists(f):
            content = open(f).read()
            lines = content.split("\n")
            # Extract frontmatter
            frontmatter = {}
            if content.startswith("---"):
                fm_block = content.split("---")[1].split("---")[0]
                for line in fm_block.split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        frontmatter[k.strip()] = v.strip()
            # Extract description (clean, without also load)
            desc_raw = frontmatter.get("description", "")
            desc_clean = desc_raw.split(" (also load:")[0].strip('"').strip("'")
            # Extract keywords
            kw_raw = frontmatter.get("keywords", "")
            keywords = set(k.strip().lower() for k in kw_raw.split(",") if k.strip())
            # Extract also load refs
            also_load = set()
            m = re.search(r'also load:\s*(.+?)(?:\)|$)', desc_raw)
            if m:
                for r in m.group(1).split(","):
                    r = r.strip().rstrip(")")
                    if r:
                        also_load.add(r)
            # Count lines
            line_count = len(lines)
            # Check for helper files
            helpers = []
            for root, _, files in os.walk(os.path.join(skills_dir, d)):
                for fn in files:
                    if fn.endswith((".py", ".sh")):
                        helpers.append(fn)
            # Extract "When" triggers
            when_section = re.search(r'## When\s*\n(.*?)(?=##|$)', content, re.DOTALL)
            triggers = set()
            if when_section:
                for m2 in re.finditer(r'"([^"]+)"', when_section.group(1)):
                    triggers.add(m2.group(1).lower())
            skills[d] = {
                "content": content,
                "lines": line_count,
                "frontmatter": frontmatter,
                "description": desc_raw,
                "description_clean": desc_clean,
                "description_len": len(desc_clean),
                "keywords": keywords,
                "also_load": also_load,
                "helpers": helpers,
                "triggers": triggers,
            }
    return skills


def audit_skills(skills_dir="skills"):
    """Full audit — frontmatter, descriptions, cross-references, helpers."""
    skills = _parse_skills(skills_dir)
    existing = set(skills.keys())
    issues = []

    # Check frontmatter
    for name, info in skills.items():
        if not info["content"].startswith("---"):
            issues.append(f"{name}: Missing frontmatter")
        for field in ["name:", "description:", "category:"]:
            if field not in info["content"].split("---")[1]:
                issues.append(f"{name}: Missing {field.strip()}")

    # Check description length
    for name, info in skills.items():
        if info["description_len"] < 30:
            issues.append(f"{name}: Short description ({info['description_len']} chars)")
        elif info["description_len"] > 200:
            issues.append(f"{name}: Long description ({info['description_len']} chars)")

    # Check line count
    for name, info in skills.items():
        if info["lines"] > 120:
            issues.append(f"{name}: Too many lines ({info['lines']})")

    # Check cross-references
    ref_graph = {}
    for name, info in skills.items():
        refs = set()
        refs |= info["also_load"] & existing
        # Check backtick refs in content
        for m in re.finditer(r'`([a-zA-Z][-_\w]*)`', info["content"]):
            if m.group(1) in existing:
                refs.add(m.group(1))
        ref_graph[name] = refs

    # Check bidirectionality
    one_way = []
    for a, refs in ref_graph.items():
        for b in refs:
            if a not in ref_graph.get(b, set()):
                one_way.append((a, b))

    # Check helpers referenced in SKILL.md but missing on disk
    for name, info in skills.items():
        for m in re.finditer(r'`([-\w]+\.(?:py|sh))`', info["content"]):
            fn = m.group(1)
            if fn not in info["helpers"]:
                issues.append(f"{name}: Helper `{fn}` referenced but not found")

    # Report
    print(f"Skills: {len(skills)}")
    print(f"Issues: {len(issues)}")
    for issue in issues:
        print(f"  ⚠ {issue}")
    print(f"One-way refs: {len(one_way)}")
    for a, b in one_way:
        print(f"  {a} → {b}")

    return len(issues) == 0 and len(one_way) == 0


def health_dashboard(skills_dir="skills"):
    """Phase 10 — print summary metrics for skill ecosystem."""
    skills = _parse_skills(skills_dir)
    if not skills:
        print("No skills found.")
        return

    total = len(skills)
    line_counts = [s["lines"] for s in skills.values()]
    desc_lens = [s["description_len"] for s in skills.values()]
    good_desc = sum(1 for l in desc_lens if 30 <= l <= 200)

    # Cross-reference density
    ref_counts = []
    for name, info in skills.items():
        refs = info["also_load"] & set(skills.keys())
        for m in re.finditer(r'`([a-zA-Z][-_\w]*)`', info["content"]):
            if m.group(1) in skills:
                refs.add(m.group(1))
        ref_counts.append(len(refs))
    avg_refs = sum(ref_counts) / total if total else 0

    # Bidirectionality
    ref_graph = {}
    for name, info in skills.items():
        refs = set()
        refs |= info["also_load"] & set(skills.keys())
        for m in re.finditer(r'`([a-zA-Z][-_\w]*)`', info["content"]):
            if m.group(1) in skills:
                refs.add(m.group(1))
        ref_graph[name] = refs
    total_refs = sum(len(v) for v in ref_graph.values())
    bidir = 0
    total_pairs = 0
    for a, refs in ref_graph.items():
        for b in refs:
            total_pairs += 1
            if a in ref_graph.get(b, set()):
                bidir += 1
    bidir_rate = (bidir / total_pairs * 100) if total_pairs else 0

    # Helper coverage
    with_helpers = sum(1 for s in skills.values() if s["helpers"])
    helper_pct = with_helpers / total * 100

    # Triggers coverage
    with_triggers = sum(1 for s in skills.values() if s["triggers"])
    trigger_pct = with_triggers / total * 100

    print("=" * 50)
    print("  SKILL HEALTH DASHBOARD")
    print("=" * 50)
    print(f"  Total skills:        {total}")
    print(f"  Avg lines/skill:     {sum(line_counts)/total:.1f}  (min={min(line_counts)}, max={max(line_counts)})")
    print(f"  Avg desc length:     {sum(desc_lens)/total:.0f} chars")
    print(f"  Desc quality:        {good_desc}/{total} ({good_desc/total*100:.0f}%) in 30-200 range")
    print(f"  Cross-ref density:   {avg_refs:.1f} refs/skill")
    print(f"  Bidirectionality:    {bidir_rate:.0f}% ({bidir}/{total_pairs} pairs)")
    print(f"  Helper coverage:     {with_helpers}/{total} ({helper_pct:.0f}%)")
    print(f"  Trigger coverage:    {with_triggers}/{total} ({trigger_pct:.0f}%)")
    print("=" * 50)


def discovery_analysis(skills_dir="skills"):
    """Phase 9 — rate each skill's findability based on description keywords."""
    skills = _parse_skills(skills_dir)
    if not skills:
        print("No skills found.")
        return

    # Common user prompt patterns to test against
    SAMPLE_PROMPTS = [
        "write a script", "shell script", "bash command",
        "review code", "code review", "python analysis",
        "search the web", "fetch a page", "look up",
        "background task", "run in background",
        "delegate", "subagent", "fork",
        "image", "screenshot", "see this",
        "plan", "task list", "project plan",
        "skill", "load skill", "what skills",
        "edit file", "read file", "write file",
        "grep", "search files", "find pattern",
        "git", "version control", "commit",
        "test", "testing", "run tests",
        "debug", "traceback", "error",
        "tmux", "terminal", "session",
        "prompt", "prompt engineering", "craft prompt",
        "maintenance", "audit", "health check",
        "documentation", "doc", "readme",
        "install", "setup", "configure",
    ]

    print("=" * 60)
    print("  SKILL DISCOVERY ANALYSIS")
    print("=" * 60)

    results = []
    for name, info in sorted(skills.items()):
        # Combine keywords + description words + triggers for matching
        desc_words = set(w.lower() for w in re.findall(r'\w+', info["description_clean"]))
        trigger_words = set(w.lower() for t in info["triggers"] for w in t.split())
        all_words = info["keywords"] | desc_words | trigger_words

        # Score: how many sample prompts match at least one word
        matches = 0
        matched_prompts = []
        for prompt in SAMPLE_PROMPTS:
            prompt_words = set(w.lower() for w in re.findall(r'\w+', prompt))
            if prompt_words & all_words:
                matches += 1
                matched_prompts.append(prompt)

        score = matches / len(SAMPLE_PROMPTS) * 100
        results.append((name, score, matches, matched_prompts))

    # Sort by score ascending (worst first)
    results.sort(key=lambda x: x[1])

    print(f"\n  {'Skill':<30} {'Score':>6} {'Matches':>8} Status")
    print(f"  {'-'*30} {'-'*6} {'-'*8} {'-'*10}")
    for name, score, matches, _ in results:
        status = "🔴 REWRITE" if score < 30 else ("🟡 IMPROVE" if score < 50 else "🟢 OK")
        print(f"  {name:<30} {score:>5.0f}% {matches:>5}/{len(SAMPLE_PROMPTS)}  {status}")

    # Detail for low-scoring skills
    print(f"\n  --- Skills needing description rewrite (score < 50) ---")
    for name, score, matches, matched in results:
        if score < 50:
            print(f"\n  {name} ({score:.0f}%):")
            print(f"    Description: {info['description_clean'][:80]}...")
            print(f"    Keywords: {', '.join(sorted(info['keywords']))[:80]}")
            print(f"    Matches: {', '.join(matched[:5])}")

    print()


def overlap_detection(skills_dir="skills"):
    """Phase 4.5 — compute Jaccard similarity between skill keyword sets, flag >60% overlap."""
    skills = _parse_skills(skills_dir)
    if len(skills) < 2:
        print("Need at least 2 skills for overlap detection.")
        return

    print("=" * 60)
    print("  SKILL OVERLAP DETECTION")
    print("=" * 60)

    # Build keyword sets (keywords + description words + triggers)
    kw_sets = {}
    for name, info in skills.items():
        desc_words = set(w.lower() for w in re.findall(r'\w+', info["description_clean"]) if len(w) > 3)
        trigger_words = set(w.lower() for t in info["triggers"] for w in t.split() if len(w) > 3)
        kw_sets[name] = info["keywords"] | desc_words | trigger_words

    # Compute Jaccard similarity for all pairs
    pairs = []
    names = sorted(kw_sets.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            intersection = kw_sets[a] & kw_sets[b]
            union = kw_sets[a] | kw_sets[b]
            jaccard = len(intersection) / len(union) if union else 0
            pairs.append((a, b, jaccard, intersection))

    # Sort by similarity descending
    pairs.sort(key=lambda x: x[2], reverse=True)

    # Flag high overlap
    high_overlap = [(a, b, s, shared) for a, b, s, shared in pairs if s > 0.6]
    medium_overlap = [(a, b, s, shared) for a, b, s, shared in pairs if 0.3 < s <= 0.6]

    print(f"\n  Total pairs: {len(pairs)}")
    print(f"  High overlap (>60%): {len(high_overlap)}")
    print(f"  Medium overlap (30-60%): {len(medium_overlap)}")

    if high_overlap:
        print(f"\n  --- HIGH OVERLAP — consider merging ---")
        for a, b, score, shared in high_overlap:
            print(f"\n  {a} ↔ {b}  ({score:.0%} overlap)")
            print(f"    Shared: {', '.join(sorted(shared)[:10])}")
            print(f"    Action: Merge if scope identical; split if divergent")

    if medium_overlap:
        print(f"\n  --- MEDIUM OVERLAP — review for differentiation ---")
        for a, b, score, shared in medium_overlap[:10]:
            print(f"  {a} ↔ {b}  ({score:.0%} overlap)  Shared: {', '.join(sorted(shared)[:5])}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Skill audit tool")
    parser.add_argument("skills_dir", nargs="?", default="skills", help="Skills directory")
    parser.add_argument("--health", action="store_true", help="Phase 10: Health dashboard")
    parser.add_argument("--discover", action="store_true", help="Phase 9: Discovery analysis")
    parser.add_argument("--overlap", action="store_true", help="Phase 4.5: Overlap detection")
    parser.add_argument("--fix", action="store_true", help="Auto-fix simple issues")
    parser.add_argument("--phase", type=int, default=0, help="Run single phase (1-10)")
    args = parser.parse_args()

    if args.health:
        health_dashboard(args.skills_dir)
    elif args.discover:
        discovery_analysis(args.skills_dir)
    elif args.overlap:
        overlap_detection(args.skills_dir)
    elif args.phase:
        # Phase-specific execution
        phase_map = {
            1: "Audit Log Analysis (requires log files)",
            2: "Skill Quality Audit",
            3: "Cross-References",
            4: "Missing Skills",
            5: "Helper File Audit",
            6: "Usage Tracking",
            7: "Description Quality",
            8: "Automation",
            9: "Skill Discovery",
            10: "Skill Health Dashboard",
        }
        label = phase_map.get(args.phase, f"Unknown Phase {args.phase}")
        print(f"Running Phase {args.phase}: {label}")
        if args.phase == 9:
            discovery_analysis(args.skills_dir)
        elif args.phase == 10:
            health_dashboard(args.skills_dir)
        elif args.phase == 4:
            overlap_detection(args.skills_dir)
        else:
            audit_skills(args.skills_dir)
    else:
        # Default: full audit
        success = audit_skills(args.skills_dir)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
