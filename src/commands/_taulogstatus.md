---
description: Log status — inspect session registry, archive stats, disk usage
---

# /_taulogstatus — Log Status

Inspect the session registry and report status.

## Phase 1: Registry Status

```bash
cd src && python3 -c "
from agent_session_registry import get_registry, LOG_DIR, REGISTRY_FILE
from pathlib import Path

registry = get_registry()
sessions = registry.list_sessions()
active = [s for s in sessions if s.get('status') == 'active']
archived = [s for s in sessions if s.get('status') == 'archived']

print('=== LOG STATUS ===')
print(f'Registry: {REGISTRY_FILE}')
print(f'Registry size: {REGISTRY_FILE.stat().st_size if REGISTRY_FILE.exists() else 0} bytes')
print()
print(f'Total sessions: {len(sessions)}')
print(f'  Active: {len(active)}')
print(f'  Archived: {len(archived)}')
print()

# Show oldest and newest
if sessions:
    oldest = min(sessions, key=lambda s: s.get('created', ''))
    newest = max(sessions, key=lambda s: s.get('created', ''))
    print(f'Oldest session: {oldest[\"prefix\"]} ({oldest.get(\"created\", \"unknown\")})')
    print(f'Newest session: {newest[\"prefix\"]} ({newest.get(\"created\", \"unknown\")})')
"
```

## Phase 2: Disk Usage

```bash
LOG_DIR="$HOME/.local/tau/log"
ARCHIVE_DIR="$LOG_DIR/archive"

echo "=== DISK USAGE ==="
echo "Log directory: $LOG_DIR"

# Calculate size of regular files (not symlinks)
LOG_SIZE=$(find "$LOG_DIR" -maxdepth 1 -type f -exec stat -c '%s' {} + 2>/dev/null | awk '{s+=$1} END {printf "%.1f MB", s/1024/1024}')
echo "  Log files (regular): ${LOG_SIZE:-0 MB}"

# Count symlinks
LINK_COUNT=$(find "$LOG_DIR" -maxdepth 1 -type l 2>/dev/null | wc -l)
echo "  Symlinks: $LINK_COUNT"

# Archive size
if [ -d "$ARCHIVE_DIR" ]; then
    ARCHIVE_SIZE=$(find "$ARCHIVE_DIR" -type f -exec stat -c '%s' {} + 2>/dev/null | awk '{s+=$1} END {printf "%.1f MB", s/1024/1024}')
    echo "  Archive: ${ARCHIVE_SIZE:-0 MB}"
    ARCHIVE_COUNT=$(find "$ARCHIVE_DIR" -type f 2>/dev/null | wc -l)
    echo "  Archive files: $ARCHIVE_COUNT"
else
    echo "  Archive: (not created yet)"
fi
```

## Phase 3: Orphan Check

```bash
cd src && python3 -c "
from agent_session_registry import get_registry
registry = get_registry()
orphans = registry.cleanup_orphans()
if orphans:
    print(f'Cleaned up {orphans} orphaned registry entries')
else:
    print('No orphaned entries found')
"
```

## Summary Report

Produce a structured report:
```
=== LOG STATUS REPORT ===
## Registry
- Total sessions: [count]
- Active: [count]
- Archived: [count]
- Oldest: [prefix] ([date])
- Newest: [prefix] ([date])

## Disk Usage
- Log files: [size]
- Symlinks: [count]
- Archive: [size]

## Cleanup
- Orphans removed: [count]
```
