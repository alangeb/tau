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
  log_dir    = ~/.local/tau/log/
  output_file = /tmp/all_user_messages.tsv
"""

import json
import os
import sys
from pathlib import Path

from _audit_parse import parse_line


def extract_prefix_from_filename(filename):
    """Extract session prefix from filename (e.g. 12345_20260705034845_1)."""
    # Format: PID_TIMESTAMP_SEQ
    parts = filename.split('_')
    if len(parts) >= 3:
        return '_'.join(parts[:3])
    return filename


def parse_audit_file(filepath):
    """Parse an audit file and yield (prefix, cwd, user_message) tuples."""
    prefix = extract_prefix_from_filename(os.path.basename(filepath))
    cwd = '?'
    in_user_block = False

    with open(filepath, 'r', errors='replace') as f:
        for raw_line in f:
            record = parse_line(raw_line)
            if record is None:
                # Continuation line — collect user content
                if in_user_block and raw_line.startswith('  | '):
                    yield (prefix, cwd, raw_line[4:].strip(), 'audit')
                continue

            # SESSION_START → extract cwd
            if record.record_type == 'SESSION_START':
                cwd = record.fields.get('cwd', '?')
                # Strip surrounding quotes if present
                if cwd.startswith("'") and cwd.endswith("'"):
                    cwd = cwd[1:-1]
                in_user_block = False
                continue

            # USER → start collecting content
            if record.record_type == 'USER':
                in_user_block = True
                continue

            # Any other record ends the user block
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

    for entry in data:
        if isinstance(entry, dict) and entry.get('role') == 'user':
            content = entry.get('content', '')
            if isinstance(content, str) and content.strip():
                yield (prefix, '?', content.strip(), 'context')


def main():
    log_dir = sys.argv[1] if len(sys.argv) > 1 else '~/.local/tau/log'
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


if __name__ == '__main__':
    main()