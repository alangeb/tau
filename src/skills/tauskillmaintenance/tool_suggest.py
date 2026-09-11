#!/usr/bin/env python3
"""tool_suggest.py — Analyze recent tool calls and suggest relevant skills to load.

Usage:
    python3 skills/tauskillmaintenance/tool_suggest.py <audit_file>
    python3 skills/tauskillmaintenance/tool_suggest.py --recent N  # Last N sessions
"""
import sys, os, re, glob
from collections import Counter, defaultdict
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent

# Tool-to-skill mapping
TOOL_MAP = {
    'bash': 'shell_scripting',
    'grep': 'grep_tool',
    'file_read': 'file-ops',
    'file_edit': 'file-ops',
    'file_write': 'file-ops',
    'ls': 'file-ops',
    'glob': 'file-ops',
    'head': 'file-ops',
    'wc': 'file-ops',
    'pyscan': 'pyprep',
    'pyanalyze': 'pyprep',
    'pygraph': 'pyprep',
    'pycheck': 'pyprep',
    'background_exec': 'background',
    'background_wait': 'background',
    'background_run': 'background',
    'background_new': 'background',
    'background_kill': 'background',
    'background_capture': 'background',
    'background_ls': 'background',
    'background_send_keys': 'background',
    'fork': 'delegation',
    'subagent': 'delegation',
    'fetch': 'web-research',
    'search': 'web-research',
    'lookup': 'web-research',
    'crawl': 'web-research',
    'see': 'image',
    'plan': 'manifest',
    'info': 'info',
    'think': 'think',
    'skill': 'skill_tool',
    'health': 'health',
    'sum': 'sum',
    'gitcrit': 'gitcrit',
    'manifest_create': 'orchestrate',
    'manifest_update': 'orchestrate',
    'manifest_tree': 'orchestrate',
    'refactor': 'refactor',
    'debug': 'debug',
    'wiki': 'wiki',
}

def parse_tools(audit_file):
    """Extract tool call counts from audit file."""
    tools = Counter()
    try:
        with open(audit_file, errors='ignore') as f:
            for line in f:
                m = re.search(r"final_name='([^']*)'", line)
                if m:
                    tools[m.group(1)] += 1
    except FileNotFoundError:
        pass
    return tools

def suggest_skills(tools, min_count=3):
    """Suggest skills based on tool usage patterns."""
    suggestions = defaultdict(int)
    for tool, count in tools.items():
        if count >= min_count and tool in TOOL_MAP:
            suggestions[TOOL_MAP[tool]] += count
    
    # Check for tool sequences
    tool_names = set(tools.keys())
    if {'pyscan', 'pygraph'}.issubset(tool_names):
        suggestions['pyprep'] += 5
    if {'file_read', 'file_edit'}.issubset(tool_names):
        suggestions['file-ops'] += 3
    if {'grep', 'bash'}.issubset(tool_names) and tools.get('grep', 0) >= 5:
        suggestions['grep_tool'] += 3
    
    return dict(sorted(suggestions.items(), key=lambda x: -x[1]))

def main():
    recent = None
    audit_file = None
    
    if '--recent' in sys.argv:
        idx = sys.argv.index('--recent')
        recent = int(sys.argv[idx + 1])
    else:
        audit_file = sys.argv[1] if len(sys.argv) > 1 else None
    
    if audit_file:
        tools = parse_tools(audit_file)
        suggestions = suggest_skills(tools)
        if suggestions:
            print(f"Suggested skills for {os.path.basename(audit_file)}:")
            for skill, score in suggestions.items():
                print(f"  skill('{skill}')  [tool score: {score}]")
        else:
            print("No skill suggestions — tool usage within normal patterns.")
    elif recent:
        # Analyze recent sessions
        log_dir = os.path.expanduser('~/.local/tau/log')
        files = sorted(glob.glob(f'{log_dir}/*.audit'), reverse=True)[:recent]
        all_suggestions = defaultdict(int)
        for f in files:
            tools = parse_tools(f)
            for skill, score in suggest_skills(tools).items():
                all_suggestions[skill] += score
        
        if all_suggestions:
            print(f"Skill suggestions across {len(files)} recent sessions:")
            for skill, score in sorted(all_suggestions.items(), key=lambda x: -x[1])[:10]:
                print(f"  skill('{skill}')  [cumulative score: {score}]")
        else:
            print("No skill suggestions across recent sessions.")

if __name__ == '__main__':
    main()
