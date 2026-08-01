---
description: Log rotation — archive old sessions, create symlinks for compatibility
---

# /_taulogrotate — Log Rotation

Archive old session files to `~/.local/tau/log/archive/YYYY-MM-DD/` and create symlinks in the original location. This keeps the log directory clean while preserving session continuity.

## Phase 1: Configuration

### 1.1 Read Retention Settings

```bash
# Default retention settings (override in tau.json under log_retention)
MAX_AGE_DAYS=30
MAX_SIZE_MB=500
ARCHIVE_DIR="$HOME/.local/tau/log/archive"
LOG_DIR="$HOME/.local/tau/log"
```

### 1.2 Create Archive Directory

```bash
mkdir -p "$ARCHIVE_DIR"
```

## Phase 2: Identify Sessions to Archive

### 2.1 Find Old Sessions

```bash
# Find sessions older than MAX_AGE_DAYS
find "$LOG_DIR" -maxdepth 1 -name "*.context" -mtime +${MAX_AGE_DAYS} -type f 2>/dev/null | \
  sed 's/\.context$//' > /tmp/archive_candidates.txt

# Also check total log directory size
LOG_SIZE_MB=$(du -sm "$LOG_DIR" 2>/dev/null | cut -f1)
echo "Log directory size: ${LOG_SIZE_MB}MB (limit: ${MAX_SIZE_MB}MB)"

# If over limit, find oldest sessions to archive
if [ "${LOG_SIZE_MB:-0}" -gt "$MAX_SIZE_MB" ]; then
  # Add older sessions to candidates (sorted by modification time)
  find "$LOG_DIR" -maxdepth 1 -name "*.context" -type f 2>/dev/null | \
    xargs ls -lt 2>/dev/null | tail -20 | awk '{print $NF}' | \
    sed 's/\.context$//' >> /tmp/archive_candidates.txt
fi

# Deduplicate
sort -u /tmp/archive_candidates.txt -o /tmp/archive_candidates.txt
echo "Sessions to archive: $(wc -l < /tmp/archive_candidates.txt)"
```

### 2.2 Check Registry

```bash
# Use registry to get session info (if available)
cd src && python3 -c "
from agent_session_registry import get_registry
registry = get_registry()
candidates = []
try:
    with open('/tmp/archive_candidates.txt') as f:
        candidates = [line.strip() for line in f if line.strip()]
    for prefix in candidates:
        session = registry.get_session(prefix)
        if session:
            print(f'{prefix}: status={session.get(\"status\")}, context={session.get(\"context\")}')
        else:
            print(f'{prefix}: NOT IN REGISTRY')
except Exception as e:
    print(f'Error: {e}')
"
```

## Phase 3: Archive Sessions

### 3.1 Move Files and Create Symlinks

```bash
# Archive each candidate session
while IFS= read -r prefix; do
  [ -z "$prefix" ] && continue
  
  # Extract date from prefix (format: {ppid}_{YYYYMMDDHHMMSS}_{N})
  timestamp=$(echo "$prefix" | cut -d'_' -f2)
  year_month_day=$(echo "$timestamp" | cut -c1-8)
  archive_date="${year_month_day:0:4}-${year_month_day:4:2}-${year_month_day:6:2}"
  
  # Create archive subdirectory
  archive_subdir="$ARCHIVE_DIR/$archive_date"
  mkdir -p "$archive_subdir"
  
  # Move files
  moved=0
  for suffix in .context .audit .plan; do
    src="$LOG_DIR/${prefix}${suffix}"
    dst="$archive_subdir/${prefix}${suffix}"
    if [ -f "$src" ]; then
      mv "$src" "$dst"
      # Create symlink
      ln -sf "$dst" "$src"
      moved=$((moved + 1))
    fi
  done
  
  # Move toolout files if any
  for toolout in "$LOG_DIR/${prefix}.toolout."*; do
    [ -f "$toolout" ] || continue
    basename=$(basename "$toolout")
    mv "$toolout" "$archive_subdir/$basename"
    ln -sf "$archive_subdir/$basename" "$toolout"
    moved=$((moved + 1))
  done
  
  # Move failed_request files if any
  for failed in "$LOG_DIR/${prefix}.failed_request.json"; do
    [ -f "$failed" ] || continue
    basename=$(basename "$failed")
    mv "$failed" "$archive_subdir/$basename"
    ln -sf "$archive_subdir/$basename" "$failed"
    moved=$((moved + 1))
  done
  
  echo "Archived $prefix to $archive_date ($moved files)"
  
  # Update registry
  cd src && python3 -c "
from agent_session_registry import get_registry
registry = get_registry()
prefix = '$prefix'
archive_subdir = '$archive_subdir'
session = registry.get_session(prefix)
if session:
    new_paths = {}
    for key in ('context', 'audit', 'plan'):
        old_path = session.get(key)
        if old_path and old_path.startswith('$LOG_DIR'):
            new_paths[key] = old_path.replace('$LOG_DIR', archive_subdir)
    if new_paths:
        registry.archive_session(prefix, new_paths)
        print(f'Updated registry for {prefix}')
" 2>/dev/null

done < /tmp/archive_candidates.txt
```

## Phase 4: Update Registry

### 4.1 Mark Archived Sessions

```bash
# Update registry to mark all archived sessions
cd src && python3 -c "
from agent_session_registry import get_registry
registry = get_registry()

try:
    with open('/tmp/archive_candidates.txt') as f:
        candidates = [line.strip() for line in f if line.strip()]
    
    updated = 0
    for prefix in candidates:
        session = registry.get_session(prefix)
        if session and session.get('status') != 'archived':
            registry.update_session(prefix, status='archived')
            updated += 1
    
    print(f'Updated {updated} sessions in registry')
except Exception as e:
    print(f'Error updating registry: {e}')
"
```

## Phase 5: Verification

### 5.1 Check Symlinks

```bash
# Verify symlinks are working
echo "=== Symlink verification ==="
broken=0
while IFS= read -r prefix; do
  [ -z "$prefix" ] && continue
  ctx="$LOG_DIR/${prefix}.context"
  if [ -L "$ctx" ]; then
    if [ ! -e "$ctx" ]; then
      echo "BROKEN: $ctx"
      broken=$((broken + 1))
    fi
  fi
done < /tmp/archive_candidates.txt

if [ "$broken" -eq 0 ]; then
  echo "All symlinks valid"
else
  echo "WARNING: $broken broken symlinks found"
fi
```

### 5.2 Check Registry Consistency

```bash
# Verify registry is consistent
cd src && python3 -c "
from agent_session_registry import get_registry
registry = get_registry()

sessions = registry.list_sessions()
archived = registry.list_sessions(status='archived')
active = registry.list_sessions(status='active')

print(f'Total sessions: {len(sessions)}')
print(f'Active: {len(active)}')
print(f'Archived: {len(archived)}')

# Check for missing files
missing = 0
for s in sessions:
    ctx = s.get('context')
    if ctx and not __import__('pathlib').Path(ctx).exists():
        missing += 1

print(f'Missing files: {missing}')
"
```

### 5.3 Summary Report

```bash
# Produce summary
echo "=== LOG ROTATION REPORT ==="
echo ""
echo "## Archive Summary"
echo "- Sessions archived: $(wc -l < /tmp/archive_candidates.txt)"
echo "- Archive directory: $ARCHIVE_DIR"
echo ""

# List archive directories
echo "## Archive Directories"
ls -la "$ARCHIVE_DIR" 2>/dev/null | tail -n +2 | while read line; do
  echo "  $line"
done
echo ""

# Current log directory size
LOG_SIZE_MB=$(du -sm "$LOG_DIR" 2>/dev/null | cut -f1)
echo "## Current Status"
echo "- Log directory size: ${LOG_SIZE_MB}MB"
echo "- Symlinks created: $(find "$LOG_DIR" -maxdepth 1 -type l 2>/dev/null | wc -l)"
echo ""

# Cleanup
rm -f /tmp/archive_candidates.txt
```

## Hard Rules
- **NEVER** delete original files without creating symlinks first
- **ALWAYS** verify symlinks work before marking complete
- **ALWAYS** update the registry after archiving
- **NEVER** archive sessions that are currently in use (check for lock files)
