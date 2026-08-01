"""Log cleanup module for TauErgon.

Manages failed_request.json files and other log artifacts to prevent
unbounded disk usage. Provides retention policies, archival, and compression.
"""

from __future__ import annotations

import gzip
import json
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_session import LOG_DIR

__all__ = [
    "DEFAULT_FAILED_REQUEST_RETENTION",
    "DEFAULT_COMPRESSION_AGE_DAYS",
    "SMALL_FILE_THRESHOLD",
    "get_failed_request_files",
    "group_by_session_prefix",
    "get_dump_dir",
    "archive_file",
    "compress_file",
    "get_file_age_days",
    "cleanup_failed_requests",
    "merge_small_failed_requests",
    "run_full_cleanup",
]

# ── Configuration ──────────────────────────────────────────────────────────────

# Default: keep last 5 failed_request.json files per session prefix
DEFAULT_FAILED_REQUEST_RETENTION = 5

# Default: compress files older than 7 days
DEFAULT_COMPRESSION_AGE_DAYS = 7

# Default: max size for "small" files to merge into daily summary (500 bytes)
SMALL_FILE_THRESHOLD = 500

# ── Core functions ─────────────────────────────────────────────────────────────

def get_failed_request_files(log_dir: Path | None = None) -> list[Path]:
    """Find all failed_request.json files in the log directory.

    Args:
        log_dir: Directory to search (defaults to LOG_DIR)

    Returns:
        List of paths to failed_request.json files
    """
    search_dir = log_dir or LOG_DIR
    if not search_dir.exists():
        return []
    return sorted(search_dir.glob("*.failed_request.json"))


def group_by_session_prefix(files: list[Path]) -> dict[str, list[Path]]:
    """Group files by session prefix (filename without .failed_request.json).

    Args:
        files: List of failed_request.json file paths

    Returns:
        Dict mapping prefix -> list of files
    """
    groups: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        prefix = f.stem  # removes .failed_request.json
        groups[prefix].append(f)
    return dict(groups)


def get_dump_dir(log_dir: Path | None = None) -> Path:
    """Get the _dump directory path, creating it if needed.

    Args:
        log_dir: Base log directory (defaults to LOG_DIR)

    Returns:
        Path to _dump subdirectory
    """
    base = log_dir or LOG_DIR
    dump_dir = base / "_dump"
    dump_dir.mkdir(parents=True, exist_ok=True)
    return dump_dir


def archive_file(filepath: Path, dump_dir: Path | None = None) -> Path | None:
    """Move a file to the _dump directory.

    Args:
        filepath: File to archive
        dump_dir: Destination directory (defaults to _dump in LOG_DIR)

    Returns:
        New path in _dump, or None on failure
    """
    if dump_dir is None:
        dump_dir = get_dump_dir()
    try:
        dest = dump_dir / filepath.name
        # Handle name conflicts by appending timestamp
        counter = 1
        while dest.exists():
            stem = filepath.stem
            suffix = filepath.suffix
            dest = dump_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        shutil.move(str(filepath), str(dest))
        return dest
    except (OSError, shutil.Error):
        return None


def compress_file(filepath: Path) -> Path | None:
    """Compress a file using gzip.

    Args:
        filepath: File to compress

    Returns:
        Path to .gz file, or None on failure
    """
    gz_path = filepath.with_suffix(filepath.suffix + ".gz")
    try:
        with open(filepath, "rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        filepath.unlink()
        return gz_path
    except (OSError, IOError):
        return None


def get_file_age_days(filepath: Path) -> float:
    """Get file age in days based on modification time.

    Args:
        filepath: File to check

    Returns:
        Age in days (float)
    """
    try:
        mtime = filepath.stat().st_mtime
        age = datetime.now() - datetime.fromtimestamp(mtime)
        return age.total_seconds() / 86400
    except OSError:
        return 0


def cleanup_failed_requests(
    log_dir: Path | None = None,
    retention: int = DEFAULT_FAILED_REQUEST_RETENTION,
    compress_age_days: int = DEFAULT_COMPRESSION_AGE_DAYS,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Clean up failed_request.json files based on retention policy.

    Policy:
    1. Keep last N files per session prefix (by modification time)
    2. Archive excess files to _dump/
    3. Compress archived files older than compress_age_days

    Args:
        log_dir: Log directory (defaults to LOG_DIR)
        retention: Number of recent files to keep per prefix
        compress_age_days: Compress files older than this many days
        dry_run: If True, don't actually modify files

    Returns:
        Dict with cleanup statistics:
        - kept: number of files kept
        - archived: number of files archived
        - compressed: number of files compressed
        - errors: list of error messages
    """
    search_dir = log_dir or LOG_DIR
    result = {"kept": 0, "archived": 0, "compressed": 0, "errors": []}

    files = get_failed_request_files(search_dir)
    if not files:
        return result

    groups = group_by_session_prefix(files)
    dump_dir = get_dump_dir(search_dir)

    for prefix, group in groups.items():
        # Sort by modification time (newest first)
        group.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        for i, filepath in enumerate(group):
            if i < retention:
                # Keep recent files
                result["kept"] += 1

                # Compress old files that are being kept
                if get_file_age_days(filepath) > compress_age_days:
                    if not dry_run:
                        gz = compress_file(filepath)
                        if gz:
                            result["compressed"] += 1
                        else:
                            result["errors"].append(f"Failed to compress: {filepath}")
                    else:
                        result["compressed"] += 1
            else:
                # Archive excess files
                if not dry_run:
                    archived = archive_file(filepath, dump_dir)
                    if archived:
                        result["archived"] += 1
                        # Compress if old enough
                        if get_file_age_days(archived) > compress_age_days:
                            gz = compress_file(archived)
                            if gz:
                                result["compressed"] += 1
                            else:
                                result["errors"].append(f"Failed to compress archived: {archived}")
                    else:
                        result["errors"].append(f"Failed to archive: {filepath}")
                else:
                    result["archived"] += 1

    return result


def merge_small_failed_requests(
    log_dir: Path | None = None,
    max_size: int = SMALL_FILE_THRESHOLD,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Merge small failed_request.json files into daily summary files.

    Files under max_size bytes are merged into daily summary files named
    failed_request_summary_YYYYMMDD.json in the _dump directory.

    Args:
        log_dir: Log directory (defaults to LOG_DIR)
        max_size: Maximum file size to consider "small" (bytes)
        dry_run: If True, don't actually modify files

    Returns:
        Dict with merge statistics:
        - merged: number of files merged
        - summaries_created: number of summary files created
        - errors: list of error messages
    """
    search_dir = log_dir or LOG_DIR
    result = {"merged": 0, "summaries_created": 0, "errors": []}

    files = get_failed_request_files(search_dir)
    if not files:
        return result

    dump_dir = get_dump_dir(search_dir)

    # Group small files by date
    daily_groups: dict[str, list[dict]] = defaultdict(list)
    files_to_remove: list[Path] = []

    for filepath in files:
        try:
            size = filepath.stat().st_size
            if size <= max_size:
                # Read the file content
                content = json.loads(filepath.read_text(encoding="utf-8"))
                timestamp = content.get("timestamp", "")
                # Extract date portion
                date_str = timestamp[:10].replace("-", "") if timestamp else "unknown"
                daily_groups[date_str].append(content)
                files_to_remove.append(filepath)
        except (json.JSONDecodeError, OSError) as e:
            result["errors"].append(f"Failed to read {filepath}: {e}")

    # Create summary files
    for date_str, records in daily_groups.items():
        summary = {
            "summary_date": date_str,
            "record_count": len(records),
            "records": records,
        }
        summary_path = dump_dir / f"failed_request_summary_{date_str}.json"

        if not dry_run:
            try:
                # Append to existing summary or create new
                if summary_path.exists():
                    existing = json.loads(summary_path.read_text(encoding="utf-8"))
                    existing["records"].extend(records)
                    existing["record_count"] = len(existing["records"])
                    summary = existing

                summary_path.write_text(
                    json.dumps(summary, indent=2, default=str), encoding="utf-8"
                )
                result["summaries_created"] += 1
            except (OSError, json.JSONDecodeError) as e:
                result["errors"].append(f"Failed to write summary for {date_str}: {e}")
        else:
            result["merged"] += len(records)
            result["summaries_created"] += 1

    # Remove original files AFTER all summaries are written (avoid double-deletion)
    if not dry_run:
        for filepath in files_to_remove:
            try:
                filepath.unlink()
                result["merged"] += 1
            except OSError as e:
                result["errors"].append(f"Failed to remove {filepath}: {e}")

    return result


def run_full_cleanup(
    log_dir: Path | None = None,
    retention: int = DEFAULT_FAILED_REQUEST_RETENTION,
    compress_age_days: int = DEFAULT_COMPRESSION_AGE_DAYS,
    merge_small: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run complete log cleanup: retention, archival, compression, and merging.

    Args:
        log_dir: Log directory (defaults to LOG_DIR)
        retention: Files to keep per session prefix
        compress_age_days: Compress files older than this
        merge_small: Merge small files into daily summaries
        dry_run: If True, report what would be done without changes

    Returns:
        Combined results from all cleanup operations
    """
    results = {"cleanup": {}, "merge": {}, "total_errors": []}

    # Run retention-based cleanup
    results["cleanup"] = cleanup_failed_requests(
        log_dir=log_dir,
        retention=retention,
        compress_age_days=compress_age_days,
        dry_run=dry_run,
    )

    # Merge small files (if enabled)
    if merge_small:
        results["merge"] = merge_small_failed_requests(
            log_dir=log_dir,
            dry_run=dry_run,
        )

    # Collect all errors
    results["total_errors"] = results["cleanup"].get("errors", []) + results["merge"].get("errors", [])

    return results


# ── CLI entry point ────────────────────────────────────────────────────────────

def main() -> int:
    """CLI entry point for log cleanup."""
    import argparse

    parser = argparse.ArgumentParser(description="Clean up TauErgon log files")
    parser.add_argument("--log-dir", type=Path, default=None, help="Log directory")
    parser.add_argument("--retention", type=int, default=DEFAULT_FAILED_REQUEST_RETENTION,
                       help=f"Files to keep per prefix (default: {DEFAULT_FAILED_REQUEST_RETENTION})")
    parser.add_argument("--compress-age", type=int, default=DEFAULT_COMPRESSION_AGE_DAYS,
                       help=f"Compress files older than N days (default: {DEFAULT_COMPRESSION_AGE_DAYS})")
    parser.add_argument("--no-merge", action="store_true", help="Skip merging small files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")

    args = parser.parse_args()

    results = run_full_cleanup(
        log_dir=args.log_dir,
        retention=args.retention,
        compress_age_days=args.compress_age,
        merge_small=not args.no_merge,
        dry_run=args.dry_run,
    )

    mode = "[DRY RUN] " if args.dry_run else ""
    print(f"{mode}Cleanup results:")
    print(f"  Kept: {results['cleanup'].get('kept', 0)}")
    print(f"  Archived: {results['cleanup'].get('archived', 0)}")
    print(f"  Compressed: {results['cleanup'].get('compressed', 0)}")
    print(f"  Merged: {results['merge'].get('merged', 0)}")
    print(f"  Summaries: {results['merge'].get('summaries_created', 0)}")

    if results["total_errors"]:
        print(f"\nErrors ({len(results['total_errors'])}):")
        for err in results["total_errors"]:
            print(f"  - {err}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
