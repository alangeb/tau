"""Tests for fetch.py redirect limit and response size limit."""

import unittest
from unittest.mock import MagicMock, patch, mock_open
from urllib.error import URLError


class TestFetchRedirectSizeLimits(unittest.TestCase):
    """Test redirect limit and response size limit in fetch.py."""

    def setUp(self):
        """Import fetch module for testing."""
        import importlib
        self.fetch = importlib.reload(__import__("tools.fetch", fromlist=["_fetch_url"]))

    def test_max_redirects_constant_exists(self):
        """Test that _MAX_REDIRECTS constant is defined."""
        self.assertTrue(hasattr(self.fetch, "_MAX_REDIRECTS"))
        self.assertEqual(self.fetch._MAX_REDIRECTS, 10)

    def test_max_response_bytes_constant_exists(self):
        """Test that _MAX_RESPONSE_BYTES constant is defined."""
        self.assertTrue(hasattr(self.fetch, "_MAX_RESPONSE_BYTES"))
        self.assertEqual(self.fetch._MAX_RESPONSE_BYTES, 50 * 1024 * 1024)  # 50 MB

    def test_read_chunk_size_constant_exists(self):
        """Test that _READ_CHUNK_SIZE constant is defined."""
        self.assertTrue(hasattr(self.fetch, "_READ_CHUNK_SIZE"))
        self.assertEqual(self.fetch._READ_CHUNK_SIZE, 64 * 1024)  # 64 KB

    def test_limited_redirect_handler_exists(self):
        """Test that _LimitedRedirectHandler class exists."""
        self.assertTrue(hasattr(self.fetch, "_LimitedRedirectHandler"))
        handler = self.fetch._LimitedRedirectHandler()
        self.assertEqual(handler._redirect_count, 0)

    def test_limited_redirect_handler_raises_after_max_redirects(self):
        """Test that _LimitedRedirectHandler raises after exceeding max redirects."""
        handler = self.fetch._LimitedRedirectHandler()
        from urllib.request import Request

        # Simulate redirects up to the limit
        for i in range(self.fetch._MAX_REDIRECTS):
            handler._redirect_count += 1

        # Next redirect should raise
        with self.assertRaises(URLError) as cm:
            handler.redirect_request(
                Request("http://example.com"),
                0, 302, "Found", {}, "http://example.com/redirect"
            )

        self.assertIn("Too many redirects", str(cm.exception))
        self.assertIn(str(self.fetch._MAX_REDIRECTS), str(cm.exception))

    def test_read_with_limit_returns_data_under_limit(self):
        """Test that _read_with_limit returns data when under size limit."""
        mock_resp = MagicMock()
        # Simulate reading chunks
        mock_resp.read.side_effect = [b"chunk1", b"chunk2", b"chunk3", b""]

        result = self.fetch._read_with_limit(mock_resp)
        self.assertEqual(result, b"chunk1chunk2chunk3")

    def test_read_with_limit_raises_on_oversized_response(self):
        """Test that _read_with_limit raises URLError on oversized response."""
        mock_resp = MagicMock()
        # Simulate reading chunks that exceed the limit
        big_chunk = b"x" * (self.fetch._MAX_RESPONSE_BYTES + 1)
        mock_resp.read.side_effect = [big_chunk, b""]

        with self.assertRaises(URLError) as cm:
            self.fetch._read_with_limit(mock_resp)

        self.assertIn("Response too large", str(cm.exception))

    def test_read_with_limit_uses_chunked_reading(self):
        """Test that _read_with_limit reads in chunks, not all at once."""
        mock_resp = MagicMock()
        chunk_size = self.fetch._READ_CHUNK_SIZE
        mock_resp.read.side_effect = [
            b"x" * chunk_size,
            b"x" * chunk_size,
            b"",
        ]

        result = self.fetch._read_with_limit(mock_resp)
        self.assertEqual(len(result), chunk_size * 2)

        # Verify read was called with chunk size
        calls = mock_resp.read.call_args_list
        self.assertTrue(all(call[0][0] == chunk_size for call in calls if call[0]))

    def test_fetch_url_uses_limited_redirect_handler(self):
        """Test that _fetch_url uses _LimitedRedirectHandler via build_opener."""
        # Check source code contains the expected pattern
        import inspect
        source = inspect.getsource(self.fetch._fetch_url)
        self.assertIn("_LimitedRedirectHandler", source)
        self.assertIn("build_opener", source)

    def test_fetch_url_uses_read_with_limit(self):
        """Test that _fetch_url uses _read_with_limit instead of resp.read()."""
        import inspect
        source = inspect.getsource(self.fetch._fetch_url)
        self.assertIn("_read_with_limit", source)
        # Make sure it doesn't use resp.read() directly (except in error handlers)
        # The main path should use _read_with_limit
        lines = source.split("\n")
        main_read = [l for l in lines if "resp.read()" in l and "_read_with_limit" not in l]
        self.assertEqual(len(main_read), 0, "resp.read() should be replaced with _read_with_limit")


if __name__ == "__main__":
    unittest.main()
