#!/usr/bin/env python3
"""Re-process all wiki sessions with improved extraction."""

import json
import os
import re
from pathlib import Path
from datetime import datetime

WIKI_DIR = Path(os.environ['HOME']) / '.local' / 'tau' / 'wiki'
# REFS_DIR is dynamic — derived from session dates at runtime

# Topic keywords for detection
TOPIC_KEYWORDS = {
    'tau': ['tau', 'tau.py', 'tauagent', 'tau-dev', 'agent.md'],
    'swe': ['swe', 'swe-bench', 'swe_lite', 'swelive'],
    'book': ['book', 'chapter', 'writing', 'manuscript'],
    'dream': ['dream', 'dream.py', 'orchestrator', 'task'],
    'llm': ['llm', 'model', 'vllm', 'ollama', 'api'],
}

def detect_topic(user_prompts, tool_calls):
    """Detect topic from content."""
    scores = {}
    all_text = ' '.join(user_prompts).lower()
    all_tools = ' '.join(tool_calls).lower()
    
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in all_text:
                scores[topic] = scores.get(topic, 0) + 1
        # Tool-based detection
        if topic == 'tau' and any(t in all_tools for t in ['pyscan', 'pyanalyze', 'pygraph']):
            scores['tau'] = scores.get('tau', 0) + 2
    
    if scores:
        return max(scores, key=scores.get)
    return 'general'

def extract_session(session_dir):
    """Extract content from a session directory."""
    result = {
        'user_prompts': [],
        'assistant_responses': [],
        'tool_calls': [],
        'errors': [],
        'session_id': session_dir.name,
    }
    
    # Try context file first (JSON format)
    context_files = list(session_dir.glob('*.context'))
    if context_files:
        try:
            with open(context_files[0]) as f:
                messages = json.load(f)
            
            for msg in messages:
                role = msg.get('role', '')
                content = msg.get('content', '')
                
                if role == 'user' and not content.startswith('# AGENT.md'):
                    result['user_prompts'].append(content[:500])  # Limit length
                elif role == 'assistant' and content:
                    clean = re.sub(r'<\|begin_of_thought\|>.*?<\|end_of_thought\|>', '', content, flags=re.DOTALL)
                    clean = clean.strip()
                    if clean and not clean.startswith('<|'):
                        result['assistant_responses'].append(clean[:500])  # Limit length
                elif role == 'tool':
                    tool_name = msg.get('name', 'unknown')
                    if tool_name not in result['tool_calls']:
                        result['tool_calls'].append(tool_name)
                    if any(kw in content.lower() for kw in ['error', 'traceback', 'connection refused', 'failed']):
                        result['errors'].append(f"{tool_name}: {content[:200]}")
        except Exception:
            pass
    
    # If no context file, parse audit file
    if not result['user_prompts']:
        audit_files = list(session_dir.glob('*.audit'))
        if audit_files:
            try:
                with open(audit_files[0]) as f:
                    content = f.read()
                
                # Extract user prompts (lines after USER nesting=)
                user_blocks = re.findall(r'USER nesting=\d+\n\s*\|\s*(.*?)(?=\n\s*\[|\n\s*USER |\n\s*TOOL_|$)', content, re.DOTALL)
                for block in user_blocks[:10]:  # Limit to 10 prompts
                    clean = block.strip().replace('\n  | ', '\n')
                    if clean and not clean.startswith('# AGENT.md'):
                        result['user_prompts'].append(clean[:500])  # Limit length
                
                # Extract tool calls
                tools = re.findall(r'TOOL_CALL.*?name=\'([^\']+)', content)
                result['tool_calls'] = list(dict.fromkeys(tools))  # Deduplicate
                
                # Extract errors
                errors = re.findall(r'\[.*?\].*?(ERROR|Traceback|Connection refused).*?\n', content)
                for err in errors[:5]:  # Limit to 5 errors
                    result['errors'].append(err.strip()[:200])
            except Exception:
                pass
    
    # Detect topic
    result['topic'] = detect_topic(result['user_prompts'], result['tool_calls'])
    
    # Extract date from session ID
    match = re.search(r'(\d{4})(\d{2})(\d{2})', session_dir.name)
    if match:
        result['date'] = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        result['week'] = get_week_number(result['date'])
    else:
        result['date'] = 'unknown'
        result['week'] = 'unknown'
    
    return result

def get_week_number(date_str):
    """Get week number from date string."""
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        # Simple week calculation (1-5)
        day = dt.day
        week = (day - 1) // 7 + 1
        return f"{dt.strftime('%Y-%m')}-w{week:02d}"
    except Exception:
        return 'unknown'

def get_refs_dir(session_data):
    """Derive references directory from session date."""
    date = session_data.get('date', 'unknown')
    if date == 'unknown':
        return WIKI_DIR / 'references' / 'unknown'
    # Extract year-month from date string (YYYY-MM-DD)
    match = re.match(r'(\d{4}-\d{2})', date)
    if match:
        return WIKI_DIR / 'references' / match.group(1)
    return WIKI_DIR / 'references' / 'unknown'

def create_content_file(session_data, topic_folder):
    """Create a wiki content file for a session."""
    topic = session_data['topic']
    week = session_data['week']
    date = session_data['date']
    
    # Create topic folder if needed
    topic_dir = WIKI_DIR / topic
    topic_dir.mkdir(exist_ok=True)
    
    # Weekly file name
    filename = f"{topic}-{week}.md"
    filepath = topic_dir / filename
    
    # Generate content
    content = f"""---
source-type: audit-log
created: {date}
updated: {date}
title: Session {session_data['session_id'].split('_')[1] if '_' in session_data['session_id'] else session_data['session_id']} — {topic.title()}
keywords: {topic}, session, audit
---

## Session {session_data['session_id'].split('_')[1] if '_' in session_data['session_id'] else session_data['session_id']}

### User Prompts
"""
    for i, prompt in enumerate(session_data['user_prompts'], 1):
        content += f"\n{i}. {prompt[:500]}{'...' if len(prompt) > 500 else ''}\n"
    
    content += "\n### Assistant Conclusions\n"
    for response in session_data['assistant_responses'][:3]:  # Limit to 3
        content += f"\n{response[:500]}{'...' if len(response) > 500 else ''}\n"
    
    content += "\n### Tools Used\n"
    content += f"- {', '.join(session_data['tool_calls'][:10])}\n"
    
    if session_data['errors']:
        content += "\n### Errors\n"
        for error in session_data['errors'][:5]:
            content += f"- {error[:200]}\n"
    
    content += f"\n### Sources\n"
    refs_dir = get_refs_dir(session_data)
    # Compute relative path from topic dir to refs dir
    rel = refs_dir.relative_to(WIKI_DIR)
    content += f"- [[../{rel}/{session_data['session_id']}/audit.md|Full Audit Log]]\n"
    
    # Append to weekly file
    if filepath.exists():
        with open(filepath, 'a') as f:
            f.write(f"\n---\n\n{content}")
    else:
        with open(filepath, 'w') as f:
            f.write(content)
    
    return filepath

def update_index(topic, week, session_data):
    """Update INDEX.md for a topic."""
    topic_dir = WIKI_DIR / topic
    index_file = topic_dir / 'INDEX.md'
    
    # Create INDEX.md if needed
    if not index_file.exists():
        with open(index_file, 'w') as f:
            f.write(f"# {topic.title()} Sessions\n\n## Weekly Files\n\n")
    
    # Read existing index
    with open(index_file) as f:
        content = f.read()
    
    # Check if week entry exists
    week_marker = f"### {week}"
    if week_marker not in content:
        # Add week entry
        session_data['session_id'].split('_')[1] if '_' in session_data['session_id'] else session_data['session_id']
        first_prompt = session_data['user_prompts'][0][:100] if session_data['user_prompts'] else 'No prompts'
        
        entry = f"""
### {week} — {first_prompt[:50]}...
Sessions from {week}. First prompt: "{first_prompt}..."
- **Keywords**: {topic}, {week}
- **File**: `{topic}-{week}.md`
- **Updated**: {session_data['date']}
"""
        # Insert before the end
        content = content.rstrip() + entry + "\n"
        
        with open(index_file, 'w') as f:
            f.write(content)

def main():
    refs_base = WIKI_DIR / 'references'
    if not refs_base.exists():
        print(f"References directory not found: {refs_base}")
        return
    
    # Collect sessions from all month directories
    sessions = []
    for month_dir in sorted(refs_base.glob('20*-*')):
        if month_dir.is_dir():
            sessions.extend(month_dir.glob('session_*'))
    
    sessions = sorted(sessions)
    print(f"Found {len(sessions)} session folders")
    
    processed = 0
    for session_dir in sessions:
        result = extract_session(session_dir)
        if result and result['user_prompts']:  # Only process sessions with user prompts
            create_content_file(result, result['topic'])
            update_index(result['topic'], result['week'], result)
            processed += 1
            if processed % 50 == 0:
                print(f"Processed {processed}/{len(sessions)} sessions...")
    
    print(f"Done! Processed {processed} sessions")

if __name__ == '__main__':
    main()
