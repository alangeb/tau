"""Shared audit log parsing utilities for tau_audit tools.

Provides a single-pass parser for the structured audit log format:
    [TIMESTAMP] RECORD_TYPE nesting=N field1=value1 field2=value2
      | continuation_line

All tau_audit analysis tools should import from this module to avoid
regex duplication and ensure consistent parsing behavior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# ── Regex patterns ────────────────────────────────────────────────────────

# Main record: [2026-08-01T09:06:30+00:00] SESSION_START nesting=0 version=1.0 ...
_RECORD_RE = re.compile(
    r'^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3})\] '
    r'(\S+) nesting=(\d+) (.*)$'
)



@dataclass
class AuditRecord:
    """Parsed audit log record."""
    timestamp: str
    record_type: str
    nesting: int
    fields: dict[str, str]
    continuations: list[str] = field(default_factory=list)


def parse_line(line: str) -> Optional[AuditRecord]:
    """Parse a single audit log line into an AuditRecord.

    Returns None for blank lines or unrecognized formats.
    Continuation lines ("  | ...") are NOT returned as separate records;
    they should be appended to the previous record's `continuations` list.
    """
    line = line.rstrip('\n')
    if not line:
        return None

    # Check for continuation line first
    if line.startswith('  | '):
        return None  # Handled by caller; see parse_file()

    m = _RECORD_RE.match(line)
    if not m:
        return None

    timestamp, record_type, nesting_str, fields_str = m.groups()
    return AuditRecord(
        timestamp=timestamp,
        record_type=record_type,
        nesting=int(nesting_str),
        fields=_parse_fields(fields_str),
    )


def _parse_fields(fields_str: str) -> dict[str, str]:
    """Split 'key=value key=value ...' into a dict.

    Handles quoted values (e.g. model='gpt-4') by splitting on '='
    only for the first '=' in each key=value pair.
    """
    result: dict[str, str] = {}
    for token in fields_str.split(' '):
        if '=' in token:
            key, value = token.split('=', 1)
            result[key] = value
    return result


def is_continuation(line: str) -> bool:
    """Return True if the line is a continuation ("  | ...")."""
    return line.startswith('  | ')


def get_continuation_text(line: str) -> str:
    """Extract the text from a continuation line (strips '  | ' prefix)."""
    return line[4:] if line.startswith('  | ') else line


def strip_quotes(s: str) -> str:
    """Strip surrounding single or double quotes from a string.

    Audit fields use Python repr-style quoting: model='gpt-4' → gpt-4
    """
    if len(s) >= 2:
        if (s[0] == "'" and s[-1] == "'") or (s[0] == '"' and s[-1] == '"'):
            return s[1:-1]
    return s


def get_field(record: AuditRecord, key: str, default: str = '') -> str:
    """Convenience: get a field value from an AuditRecord."""
    return record.fields.get(key, default)


def get_field_int(record: AuditRecord, key: str, default: int = 0) -> int:
    """Convenience: get a field value as int from an AuditRecord."""
    try:
        return int(record.fields[key])
    except (KeyError, ValueError):
        return default


def get_field_float(record: AuditRecord, key: str, default: float = 0.0) -> float:
    """Convenience: get a field value as float from an AuditRecord."""
    try:
        return float(record.fields[key])
    except (KeyError, ValueError):
        return default