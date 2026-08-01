#!/usr/bin/env python3
"""Extract structured content from tau session context files.

Usage:
    python3 wiki_extract.py <session_dir> [--json]
    python3 wiki_extract.py --batch <references_dir> <output_dir>

Parses context.json files (JSON array of messages) to extract:
- ALL user prompts
- ALL assistant responses
- ALL tool calls
- Session metadata
"""

import argparse
import json
import re
from pathlib import Path


def parse_context_file(filepath):
    """Parse a context JSON file and extract structured content."""
    result = {
        'user_prompts': [],
        'assistant_responses': [],
        'tool_calls': [],
        'errors': [],
        'metadata': {},
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            messages = json.load(f)
    except Exception as e:
        result['parse_error'] = str(e)
        return result

    for msg in messages:
        role = msg.get('role', '')
        content = msg.get('content', '')

        if role == 'user':
            # Extract user prompt (skip system messages)
            if content and not content.startswith('# AGENT.md'):
                result['user_prompts'].append(content)

        elif role == 'assistant':
            # Extract assistant response
            if content:
                # Remove thinking tags
                clean = re.sub(r'<\|begin_of_thought\|>.*?<\|end_of_thought\|>', '', content, flags=re.DOTALL)
                clean = clean.strip()
                if clean:
                    result['assistant_responses'].append(clean)

        elif role == 'tool':
            # Extract tool results
            tool_name = msg.get('name', 'unknown')
            if tool_name not in result['tool_calls']:
                result['tool_calls'].append(tool_name)
            # Check for errors in tool results
            if 'error' in content.lower() or 'traceback' in content.lower() or 'connection refused' in content.lower():
                result['errors'].append(f"{tool_name}: {content[:200]}")

    # Extract metadata from first user message
    if result['user_prompts']:
        result['metadata']['first_prompt'] = result['user_prompts'][0][:100]

    return result


def detect_topic(extracted):
    """Detect topic from extracted content."""
    topic_scores = {}

    all_text = ' '.join(extracted['user_prompts']).lower()
    all_tools = ' '.join(extracted['tool_calls']).lower()

    # Check for project keywords
    keywords = {
        'tau': ['tau', 'tau.py', 'tauagent', 'tau-dev'],
        'swe': ['swe', 'swe-bench', 'swe_lite', 'swelive'],
        'book': ['book', 'chapter', 'writing'],
        'dream': ['dream', 'dream.py', 'orchestrator'],
        'llm': ['llm', 'model', 'api', 'vllm', 'ollama'],
        'skill': ['skill', 'skills', 'wiki'],
    }

    for topic, words in keywords.items():
        for word in words:
            if word in all_text:
                topic_scores[topic] = topic_scores.get(topic, 0) + 1

    # Check tool patterns
    if any(t in all_tools for t in ['pyscan', 'pyanalyze', 'pygraph']):
        topic_scores['tau'] = topic_scores.get('tau', 0) + 1

    if topic_scores:
        return max(topic_scores, key=topic_scores.get)
    return 'general'


def extract_from_session_dir(session_dir):
    """Extract content from a session directory."""
    session_dir = Path(session_dir)

    # Find context file
    context_file = None
    for ext in ['.context', '.json']:
        candidates = list(session_dir.glob(f'*{ext}'))
        if candidates:
            context_file = candidates[0]
            break

    if not context_file:
        return None

    return parse_context_file(context_file)


def main():
    parser = argparse.ArgumentParser(description='Extract content from tau session context files')
    parser.add_argument('input', nargs='?', help='Session directory')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--batch', nargs=2, metavar=('INPUT_DIR', 'OUTPUT_DIR'), help='Batch mode')
    args = parser.parse_args()

    if args.batch:
        input_dir, output_dir = args.batch
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        sessions = sorted(input_dir.glob('session_*'))
        count = 0
        for session_dir in sessions:
            result = extract_from_session_dir(session_dir)
            if result and not result.get('parse_error'):
                output_file = output_dir / f'{session_dir.name}.json'
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2)
                count += 1
                if count % 100 == 0:
                    print(f'Processed {count} sessions...')

        print(f'Total: {count} sessions extracted')
    elif args.input:
        result = extract_from_session_dir(Path(args.input))
        if result:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"User prompts: {len(result['user_prompts'])}")
                print(f"Assistant responses: {len(result['assistant_responses'])}")
                print(f"Tool calls: {len(result['tool_calls'])}")
                print(f"Errors: {len(result['errors'])}")
                if result['user_prompts']:
                    print(f"\nFirst prompt: {result['user_prompts'][0][:200]}")
        else:
            print("No context file found")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
