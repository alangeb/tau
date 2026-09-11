#!/usr/bin/env python3
"""Analyze skill load rates from audit logs. Compute per-skill load frequency and suggest improvements."""
import os, re, sys, glob as glob_mod
from collections import Counter

LOG_DIR = os.path.expanduser('~/.local/tau/log')

def get_audit_files(max_files=50):
    """Get recent audit files."""
    files = sorted(glob_mod.glob(os.path.join(LOG_DIR, '*_1.audit')), reverse=True)[:max_files]
    return files

def count_tool_calls(audit_files):
    """Count all tool calls across audit files."""
    tools = Counter()
    skills_loaded = Counter()
    for f in audit_files:
        if not os.path.exists(f):
            continue
        with open(f) as fh:
            content = fh.read()
        # Count all tool calls
        for m in re.finditer(r"final_name='([^']*)'", content):
            tools[m.group(1)] += 1
        # Count skill loads with names
        for m in re.finditer(r"final_name='skill'.*?skill_name=['\"]?([^'\",}\s]*)", content, re.DOTALL):
            name = m.group(1).strip()
            if name:
                skills_loaded[name] += 1
    return tools, skills_loaded

def analyze(max_files=50):
    """Analyze skill load rates."""
    audit_files = get_audit_files(max_files)
    if not audit_files:
        print(f"No audit files found in {LOG_DIR}")
        return
    
    tools, skills_loaded = count_tool_calls(audit_files)
    total_tools = sum(tools.values())
    total_skill_calls = tools.get('skill', 0)
    load_rate = (total_skill_calls / total_tools * 100) if total_tools else 0
    
    print(f"=== Skill Load Rate Analysis ({len(audit_files)} sessions) ===")
    print(f"Total tool calls: {total_tools}")
    print(f"Total skill calls: {total_skill_calls}")
    print(f"Skill load rate: {load_rate:.2f}%")
    print(f"Target: >1%")
    print()
    
    # Top tools
    print("Top 10 tools by frequency:")
    for tool, count in tools.most_common(10):
        pct = count / total_tools * 100
        print(f"  {tool:25s} {count:5d} ({pct:5.1f}%)")
    print()
    
    # Skills loaded
    if skills_loaded:
        print("Skills loaded (by name):")
        for name, count in skills_loaded.most_common(20):
            print(f"  {name:25s} {count:5d}")
    else:
        print("No named skill loads found")
    print()
    
    # Recommendations
    print("=== Recommendations ===")
    if load_rate < 1:
        print(f"  CRITICAL: Load rate {load_rate:.2f}% < 1% target")
        print("  Actions:")
        print("    1. Inject skill prompts into AGENT.md (see tauskillmaintenance skill)")
        print("    2. Rewrite skill descriptions with natural language")
        print("    3. Add auto-load triggers for common tool patterns")
    
    # Check for tools without skill coverage
    tool_skill_map = {
        'bash': 'shell_scripting', 'grep': 'grep_tool', 'file_read': 'file-ops',
        'file_edit': 'file-ops', 'file_write': 'file-ops', 'ls': 'file-ops',
        'glob': 'file-ops', 'head': 'file-ops', 'wc': 'file-ops',
        'background_exec': 'background', 'background_wait': 'background',
        'background_run': 'background', 'subagent': 'delegation', 'fork': 'delegation',
        'pyscan': 'pyprep', 'pygraph': 'pyprep',
        'pyanalyze': 'pyprep', 'plan': 'manifest',
        'fetch': 'web-research', 'search': 'web-research', 'see': 'image',
    }
    
    print()
    print("High-frequency tools and their skills:")
    for tool, count in tools.most_common(15):
        skill = tool_skill_map.get(tool, '(none)')
        print(f"  {tool:25s} {count:5d} calls → {skill}")

if __name__ == '__main__':
    max_files = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    analyze(max_files)
