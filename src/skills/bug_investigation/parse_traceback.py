#!/usr/bin/env python3
"""Parse traceback files and extract error information."""
import re, sys, json

def parse_traceback(text):
    result = {
        'exception_type': None,
        'exception_msg': None,
        'frames': [],
        'file_line_pairs': []
    }
    
    # Extract exception type and message
    exc_match = re.search(r'Traceback \(most recent call last\):?\s*\n.*?\n(\w+Error|\w+Exception): (.*)', text, re.DOTALL)
    if exc_match:
        result['exception_type'] = exc_match.group(1)
        result['exception_msg'] = exc_match.group(2).strip()
    
    # Extract frames
    for m in re.finditer(r'File "([^"]+)", line (\d+), in (\w+)\s*\n\s*(.+)', text):
        result['frames'].append({
            'file': m.group(1),
            'line': int(m.group(2)),
            'function': m.group(3),
            'code': m.group(4).strip()
        })
        result['file_line_pairs'].append((m.group(1), int(m.group(2))))
    
    return result

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: investigate.py <traceback.txt>")
        sys.exit(1)
    
    with open(sys.argv[1]) as f:
        tb = f.read()
    
    result = parse_traceback(tb)
    print(json.dumps(result, indent=2))
