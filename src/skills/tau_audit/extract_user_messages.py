#!/usr/bin/env python3
"""Extract all user messages from Tau audit and context log files.

Reads all .audit and .context files in a log directory, extracts user messages
along with the working directory (cwd) where each session was executed.

Output format (TSV):
  session_prefix\tcwd\tuser_message\tsource

Where source is 'audit' or 'context'.

Usage:
  python3 extract_user_messages.py [log_dir] [output_file]

Defaults:
  log_dir    = /home/alangeb/.local/tau/log/
  output_file = /tmp/all_user_messages.tsv
"""

import json
import os
import re
import sys
from pathlib import Path


# Regex patterns for audit file parsing
AUDIT_SESSION_START_RE = re.compile(
    r'^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)\]\s+SESSION_START\s+(.*)'
)
AUDIT_CWD_RE = re.compile(r"cwd='([^']+)'\s*")
AUDIT_USER_LINE_RE = re.compile(r'^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)\]\s+USER\s*(.*)')

# Regex to extract session prefix from filename
PREFIX_RE = re.compile(r'^(\d+_\d{14}_\d+)')


def extract_cwd_from_session_start(line):
    """Extract cwd from a SESSION_START line."""
    m = AUDIT_CWD_RE.search(line)
    return m.group(1) if m else '?'


def extract_prefix_from_filename(filename):
    """Extract session prefix from filename."""
    m = PREFIX_RE.match(filename)
    return m.group(1) if m else filename


def parse_audit_file(filepath):
    """Parse an audit file and yield (prefix, cwd, user_message) tuples."""
    prefix = extract_prefix_from_filename(os.path.basename(filepath))
    cwd = '?'
    in_user_block = False

    with open(filepath, 'r', errors='replace') as f:
        for line in f:
            # Check for SESSION_START to get cwd
            if 'SESSION_START' in line:
                cwd = extract_cwd_from_session_start(line) or '?'

            # Check for USER line
            m = AUDIT_USER_LINE_RE.match(line)
            if m:
                in_user_block = True
                # Content is on the next line(s)
                continue

            # If we're in a user block, read content
            if in_user_block and line.startswith('  | '):
                yield (prefix, cwd, line[4:].strip(), 'audit')
                continue

            # Any non-content line ends the user block
            if in_user_block and not line.startswith('  | '):
                in_user_block = False


def parse_context_file(filepath):
    """Parse a context file and yield (prefix, cwd, user_message) tuples."""
    prefix = extract_prefix_from_filename(os.path.basename(filepath))

    try:
        with open(filepath, 'r', errors='replace') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return

    if not isinstance(data, list):
        return

    # Extract cwd from system prompt if present
    cwd = '?'
    for entry in data:
        if isinstance(entry, dict) and entry.get('role') == 'system':
            content = entry.get('content', '')
            if isinstance(content, str):
                cwd_m = re.search(r"Log file:\s*(\S+\.audit)", content)
                if cwd_m:
                    # Try to extract cwd from log file path in system prompt
                    pass

    for entry in data:
        if isinstance(entry, dict) and entry.get('role') == 'user':
            content = entry.get('content', '')
            if isinstance(content, str) and content.strip():
                yield (prefix, cwd, content.strip(), 'context')


def main():
    log_dir = sys.argv[1] if len(sys.argv) > 1 else '/home/alangeb/.local/tau/log'
    output_file = sys.argv[2] if len(sys.argv) > 2 else '/tmp/all_user_messages.tsv'

    log_path = Path(log_dir)
    if not log_path.exists():
        print(f"Error: Log directory '{log_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    audit_files = sorted(log_path.glob('*.audit'))
    context_files = sorted(log_path.glob('*.context'))

    print(f"Found {len(audit_files)} audit files, {len(context_files)} context files", file=sys.stderr)

    total_users = 0
    seen = set()  # Dedup by (prefix, message)

    with open(output_file, 'w') as out:
        # Header
        out.write('session_prefix\tcwd\tsource\tuser_message\n')

        # Process audit files first (they have cwd info)
        for af in audit_files:
            for prefix, cwd, msg, source in parse_audit_file(str(af)):
                key = (prefix, msg)
                if key not in seen:
                    seen.add(key)
                    out.write(f'{prefix}\t{cwd}\t{source}\t{msg}\n')
                    total_users += 1

        # Process context files (may have additional user messages not in audit)
        for cf in context_files:
            for prefix, cwd, msg, source in parse_context_file(str(cf)):
                key = (prefix, msg)
                if key not in seen:
                    seen.add(key)
                    out.write(f'{prefix}\t{cwd}\t{source}\t{msg}\n')
                    total_users += 1

    print(f"Extracted {total_users} unique user messages to '{output_file}'", file=sys.stderr)

    # Stats
    audit_count = sum(1 for _ in open(output_file)) - 1  # minus header
    print(f"Total lines (including header): {audit_count + 1}", file=sys.stderr)


if __name__ == '__main__':
    main()