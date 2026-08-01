"""Tests for agent_log_cleanup module."""
import gzip
import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest import TestCase

from agent_log_cleanup import (
    DEFAULT_FAILED_REQUEST_RETENTION,
    DEFAULT_COMPRESSION_AGE_DAYS,
    SMALL_FILE_THRESHOLD,
    archive_file,
    cleanup_failed_requests,
    compress_file,
    get_dump_dir,
    get_failed_request_files,
    get_file_age_days,
    group_by_session_prefix,
    merge_small_failed_requests,
    run_full_cleanup,
)


class TestGetFailedRequestFiles(TestCase):
    def test_finds_files(self):
        with self._temp_dir() as d:
            (d / "prefix1.failed_request.json").write_text("{}")
            (d / "prefix2.failed_request.json").write_text("{}")
            (d / "other.txt").write_text("nope")
            result = get_failed_request_files(d)
            self.assertEqual(len(result), 2)
    
    def test_empty_dir(self):
        with self._temp_dir() as d:
            result = get_failed_request_files(d)
            self.assertEqual(result, [])
    
    def test_nonexistent_dir(self):
        result = get_failed_request_files(Path("/nonexistent_tau_dir_12345"))
        self.assertEqual(result, [])
    
    @staticmethod
    def _temp_dir():
        d = tempfile.TemporaryDirectory()
        return _TempDirWrapper(d)


class _TempDirWrapper:
    """Wrapper to return a Path from TemporaryDirectory context manager."""
    def __init__(self, td):
        self._td = td
    def __enter__(self):
        return Path(self._td.__enter__())
    def __exit__(self, *args):
        self._td.__exit__(*args)


class TestGroupBySessionPrefix(TestCase):
    def test_groups_correctly(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            files = [
                d / "prefix1_123.failed_request.json",
                d / "prefix1_456.failed_request.json",
                d / "prefix2_789.failed_request.json",
            ]
            for f in files:
                f.write_text("{}")
            groups = group_by_session_prefix(files)
            # f.stem strips only the last extension (.json), so each file
            # gets its own group since all stems are unique
            self.assertEqual(len(groups), 3)
            self.assertIn("prefix1_123.failed_request", groups)
            self.assertIn("prefix1_456.failed_request", groups)
            self.assertIn("prefix2_789.failed_request", groups)


class TestGetDumpDir(TestCase):
    def test_creates_dir(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            dump = get_dump_dir(d)
            self.assertTrue(dump.exists())
            self.assertEqual(dump, d / "_dump")


class TestArchiveFile(TestCase):
    def test_moves_file(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = d / "test.failed_request.json"
            src.write_text("data")
            dump = get_dump_dir(d)
            result = archive_file(src, dump)
            self.assertIsNotNone(result)
            self.assertTrue(result.exists())
            self.assertFalse(src.exists())
            self.assertEqual(result.read_text(), "data")
    
    def test_handles_name_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            dump = get_dump_dir(d)
            # Create existing file in dump
            (dump / "test.failed_request.json").write_text("existing")
            src = d / "test.failed_request.json"
            src.write_text("new")
            result = archive_file(src, dump)
            self.assertIsNotNone(result)
            self.assertTrue(result.exists())
            self.assertEqual(result.read_text(), "new")


class TestCompressFile(TestCase):
    def test_compresses(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = d / "test.failed_request.json"
            content = json.dumps({"key": "value" * 100})
            src.write_text(content)
            result = compress_file(src)
            self.assertIsNotNone(result)
            self.assertTrue(result.exists())
            self.assertFalse(src.exists())
            self.assertTrue(str(result).endswith(".gz"))
            # Verify content
            with gzip.open(result, "rt") as f:
                self.assertEqual(f.read(), content)


class TestGetFileAgeDays(TestCase):
    def test_new_file(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            f = d / "test.txt"
            f.write_text("new")
            age = get_file_age_days(f)
            self.assertLess(age, 0.001)  # Less than a second old


class TestCleanupFailedRequests(TestCase):
    def test_keeps_recent_files(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            # Create 7 files — each has a unique stem, so each is in its own group
            # With retention=5, each group (size 1) keeps its only file
            for i in range(7):
                f = d / f"prefix_{i}.failed_request.json"
                f.write_text(json.dumps({"index": i}))
                os.utime(f, (time.time() - (7-i)*3600, time.time() - (7-i)*3600))
            
            result = cleanup_failed_requests(d, retention=5, compress_age_days=999)
            
            # All 7 kept since each is in its own group of size 1 (< retention)
            self.assertEqual(result["kept"], 7)
            self.assertEqual(result["archived"], 0)
            self.assertEqual(len(result["errors"]), 0)
    
    def test_archives_to_dump(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            # Since each file has a unique stem, each is in its own group.
            # With retention=0, all files should be archived.
            for i in range(10):
                f = d / f"prefix_{i}.failed_request.json"
                f.write_text(json.dumps({"index": i}))
                os.utime(f, (time.time() - (10-i)*3600, time.time() - (10-i)*3600))
            
            cleanup_failed_requests(d, retention=0, compress_age_days=999)
            
            # Check _dump has archived files
            dump = d / "_dump"
            self.assertTrue(dump.exists())
            archived = list(dump.glob("*.failed_request.json"))
            self.assertEqual(len(archived), 10)
    
    def test_dry_run_no_changes(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for i in range(5):
                f = d / f"prefix_{i}.failed_request.json"
                f.write_text(json.dumps({"index": i}))
                os.utime(f, (time.time() - (5-i)*3600, time.time() - (5-i)*3600))
            
            initial_count = len(list(d.glob("*.failed_request.json")))
            # retention=0 means all should be archived (in non-dry-run)
            result = cleanup_failed_requests(d, retention=0, dry_run=True)
            
            final_count = len(list(d.glob("*.failed_request.json")))
            self.assertEqual(initial_count, final_count)
            self.assertEqual(result["archived"], 5)


class TestMergeSmallFailedRequests(TestCase):
    def test_merges_small_files(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            today = datetime.now().strftime("%Y-%m-%d")
            date_str = today.replace("-", "")
            
            # Create small files
            for i in range(3):
                f = d / f"prefix_{i}.failed_request.json"
                content = json.dumps({
                    "timestamp": f"{today}T12:00:{i:02d}",
                    "data": f"test{i}"
                })
                f.write_text(content)
            
            result = merge_small_failed_requests(d, dry_run=False)
            
            self.assertEqual(result["merged"], 3)
            self.assertEqual(result["summaries_created"], 1)
            
            # Check summary exists
            summary = d / "_dump" / f"failed_request_summary_{date_str}.json"
            self.assertTrue(summary.exists())
            
            data = json.loads(summary.read_text())
            self.assertEqual(data["record_count"], 3)
    
    def test_skips_large_files(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Create large file (>500 bytes)
            f = d / "prefix_large.failed_request.json"
            content = json.dumps({"data": "x" * 1000})
            f.write_text(content)
            
            result = merge_small_failed_requests(d, dry_run=False)
            
            self.assertEqual(result["merged"], 0)
            self.assertTrue(f.exists())  # Should not be removed


class TestRunFullCleanup(TestCase):
    def test_runs_all_steps(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Create mix of files
            for i in range(8):
                f = d / f"prefix_{i}.failed_request.json"
                if i < 3:
                    # Small files for merging
                    content = json.dumps({
                        "timestamp": f"{today}T12:00:{i:02d}",
                        "data": f"small{i}"
                    })
                else:
                    # Large files for retention
                    content = json.dumps({"data": "x" * 1000})
                f.write_text(content)
                os.utime(f, (time.time() - (8-i)*3600, time.time() - (8-i)*3600))
            
            result = run_full_cleanup(d, retention=5, compress_age_days=999, dry_run=False)
            
            self.assertIn("cleanup", result)
            self.assertIn("merge", result)
            self.assertIn("total_errors", result)


if __name__ == "__main__":
    import tempfile
    import unittest
    unittest.main()
