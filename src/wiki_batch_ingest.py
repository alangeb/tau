#!/usr/bin/env python3
"""Batch process unprocessed sessions from log directory into wiki."""

import json
import os
import re
import shutil
from pathlib import Path
from datetime import datetime

LOG_DIR = Path(os.environ['HOME']) / '.local' / 'tau' / 'log'
WIKI_DIR = Path(os.environ['HOME']) / '.local' / 'tau' / 'wiki'
REFS_DIR = WIKI_DIR / 'references'
DUMP_DIR = WIKI_DIR / '_dump'

TOPIC_KEYWORDS = {
    'tau': ['tau', 'tau.py', 'tauagent', 'tau-dev', 'agent.md', 'tauergon'],
    'swe': ['swe', 'swe-bench', 'swe_lite', 'swelive', 'sweep'],
    'book': ['book', 'chapter', 'writing', 'manuscript', 'novel'],
    'dream': ['dream', 'dream.py', 'orchestrator', 'dreamcycle'],
    'llm': ['llm', 'model', 'vllm', 'ollama', 'api', 'inference'],
    'skill': ['skill', 'skills', 'wiki', 'skill.md'],
}

def get_session_files(group_key):
    files = {}
    for f in LOG_DIR.glob(f'{group_key}_*.audit'):
        files['audit'] = f
    for f in LOG_DIR.glob(f'{group_key}_*.context'):
        files['context'] = f
    for f in LOG_DIR.glob(f'{group_key}_*.lr.json'):
        files['lr_json'] = f
    for f in LOG_DIR.glob(f'{group_key}_*.failed_request.json'):
        files['failed'] = f
    for f in LOG_DIR.glob(f'{group_key}_*.plan'):
        files['plan'] = f
    return files

def parse_context_file(filepath):
    result = {'user_prompts': [], 'assistant_responses': [], 'tool_calls': [], 'errors': []}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            if role == 'user' and content and not content.startswith('# AGENT.md'):
                result['user_prompts'].append(content[:1000])
            elif role == 'assistant' and content:
                clean = re.sub(r'<\|begin_of_thought\|>.*?<\|end_of_thought\|>', '', content, flags=re.DOTALL)
                clean = clean.strip()
                if clean and not clean.startswith('<|'):
                    result['assistant_responses'].append(clean[:1000])
            elif role == 'tool':
                tool_name = msg.get('name', 'unknown')
                if tool_name not in result['tool_calls']:
                    result['tool_calls'].append(tool_name)
                if any(kw in content.lower() for kw in ['error', 'traceback', 'connection refused', 'failed']):
                    result['errors'].append(f"{tool_name}: {content[:200]}")
    except Exception:
        pass
    return result

def parse_audit_file(filepath):
    result = {'user_prompts': [], 'assistant_responses': [], 'tool_calls': [], 'errors': []}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        user_blocks = re.findall(r'USER nesting=\d+\n\s*\|\s*(.*?)(?=\n\s*\[|\n\s*USER |\n\s*TOOL_|$)', content, re.DOTALL)
        for block in user_blocks[:10]:
            clean = block.strip().replace('\n  | ', '\n')
            if clean and not clean.startswith('# AGENT.md'):
                result['user_prompts'].append(clean[:1000])
        tools = re.findall(r'TOOL_CALL.*?name=\'([^\']+)', content)
        result['tool_calls'] = list(dict.fromkeys(tools))
        errors = re.findall(r'\[.*?\].*?(ERROR|Traceback|Connection refused).*?\n', content)
        for err in errors[:5]:
            result['errors'].append(err.strip()[:200])
    except Exception:
        pass
    return result

def detect_topic(user_prompts, tool_calls):
    scores = {}
    all_text = ' '.join(user_prompts).lower()
    all_tools = ' '.join(tool_calls).lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in all_text:
                scores[topic] = scores.get(topic, 0) + 1
        if topic == 'tau' and any(t in all_tools for t in ['pyscan', 'pyanalyze', 'pygraph']):
            scores['tau'] = scores.get('tau', 0) + 2
    if scores:
        return max(scores, key=scores.get)
    return 'general'

def get_date_week(session_id):
    match = re.search(r'(\d{4})(\d{2})(\d{2})', session_id)
    if match:
        date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            week = (dt.day - 1) // 7 + 1
            return date_str, f"{dt.strftime('%Y-%m')}-w{week:02d}"
        except:
            pass
    return 'unknown', 'unknown'

def is_valuable(extracted):
    if len(extracted['user_prompts']) <= 1 and not extracted['errors']:
        first_prompt = extracted['user_prompts'][0].lower() if extracted['user_prompts'] else ''
        if any(kw in first_prompt for kw in ['hello', 'hi', 'thanks', 'thank', 'bye', 'exit', 'status']):
            return False
    if extracted['errors'] or len(extracted['user_prompts']) > 1:
        return True
    if len(extracted['tool_calls']) > 2:
        return True
    return False

def copy_session_files(group_key, dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    files = get_session_files(group_key)
    copied = 0
    for ftype, filepath in files.items():
        dest = dest_dir / filepath.name
        shutil.copy2(filepath, dest)
        copied += 1
    return copied

def create_wiki_content(extracted, session_id, topic, date, week):
    topic_dir = WIKI_DIR / topic
    topic_dir.mkdir(exist_ok=True)
    filename = f"{topic}-{week}.md"
    filepath = topic_dir / filename
    
    content = f"""---
source-type: audit-log
created: {date}
updated: {date}
title: Session {session_id} — {topic.title()}
keywords: {topic}, session, audit
---

## Session {session_id}

### User Prompts
"""
    for i, prompt in enumerate(extracted['user_prompts'][:5], 1):
        content += f"\n{i}. {prompt[:500]}{'...' if len(prompt) > 500 else ''}\n"
    
    content += "\n### Assistant Conclusions\n"
    for response in extracted['assistant_responses'][:3]:
        content += f"\n{response[:500]}{'...' if len(response) > 500 else ''}\n"
    
    content += "\n### Tools Used\n"
    content += f"- {', '.join(extracted['tool_calls'][:10])}\n"
    
    if extracted['errors']:
        content += "\n### Errors\n"
        for error in extracted['errors'][:5]:
            content += f"- {error[:200]}\n"
    
    if filepath.exists():
        with open(filepath, 'a') as f:
            f.write(f"\n---\n\n{content}")
    else:
        with open(filepath, 'w') as f:
            f.write(content)
    
    return filepath

def update_topic_index(topic, week, session_id, first_prompt):
    topic_dir = WIKI_DIR / topic
    index_file = topic_dir / 'INDEX.md'
    
    if not index_file.exists():
        with open(index_file, 'w') as f:
            f.write(f"# {topic.title()} Sessions\n\n## Weekly Files\n\n")
    
    with open(index_file) as f:
        content = f.read()
    
    week_marker = f"### {week}"
    if week_marker not in content:
        entry = f"""
### {week}
- Session {session_id}: {first_prompt[:100]}...
- **File**: `{topic}-{week}.md`
- **Updated**: {datetime.now().strftime('%Y-%m-%d')}
"""
        content = content.rstrip() + entry + "\n"
        with open(index_file, 'w') as f:
            f.write(content)

def main():
    print(f"Processing sessions from {LOG_DIR}")
    print(f"Wiki at {WIKI_DIR}")
    
    groups = {}
    for f in LOG_DIR.glob('*.audit'):
        parts = f.stem.rsplit('_', 2)
        if len(parts) >= 2:
            key = f'{parts[0]}_{parts[1]}'
            if key not in groups:
                groups[key] = []
            groups[key].append(f)
    
    sorted_groups = sorted(groups.keys(), reverse=True)
    print(f"Found {len(sorted_groups)} session groups")
    
    processed = 0
    valuable = 0
    trivial = 0
    errors = 0
    
    for group_key in sorted_groups:
        try:
            files = get_session_files(group_key)
            if not files:
                continue
            
            extracted = {}
            if 'context' in files:
                extracted = parse_context_file(files['context'])
            elif 'audit' in files:
                extracted = parse_audit_file(files['audit'])
            
            if not extracted.get('user_prompts'):
                trivial += 1
                processed += 1
                continue
            
            topic = detect_topic(extracted['user_prompts'], extracted['tool_calls'])
            date, week = get_date_week(group_key)
            
            if is_valuable(extracted):
                refs_month = WIKI_DIR / 'references' / date[:7] if date != 'unknown' else WIKI_DIR / 'references' / 'unknown'
                session_dir = refs_month / group_key
                copy_session_files(group_key, session_dir)
                create_wiki_content(extracted, group_key, topic, date, week)
                first_prompt = extracted['user_prompts'][0][:100] if extracted['user_prompts'] else ''
                update_topic_index(topic, week, group_key, first_prompt)
                valuable += 1
            else:
                dump_dir = DUMP_DIR / group_key
                copy_session_files(group_key, dump_dir)
                trivial += 1
            
            processed += 1
            if processed % 50 == 0:
                print(f"Processed {processed}/{len(sorted_groups)} (valuable: {valuable}, trivial: {trivial})")
            
        except Exception as e:
            errors += 1
            if errors <= 10:
                print(f"Error processing {group_key}: {e}")
    
    print(f"\nDone! Processed {processed} sessions")
    print(f"  Valuable: {valuable}")
    print(f"  Trivial: {trivial}")
    print(f"  Errors: {errors}")

if __name__ == '__main__':
    main()