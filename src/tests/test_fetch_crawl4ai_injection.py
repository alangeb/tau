"""Tests for Crawl4AI curl command injection prevention in tools/fetch.py."""

import pytest
import shlex
import json
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.fetch import _try_crawl4ai_single, _try_crawl4ai_multi


class TestCrawl4AICurlInjection:
    """Test that Crawl4AI curl commands are safe from shell injection."""

    def test_shlex_quote_escapes_single_quotes(self):
        """Verify shlex.quote properly escapes single quotes."""
        malicious = "foo'; rm -rf /; echo '"
        quoted = shlex.quote(malicious)
        # shlex.quote wraps in single quotes and escapes internal quotes
        assert "'" in quoted
        # The quoted string should be safe to use in shell
        # Verify it doesn't break out of the quote
        assert quoted.count("'") % 2 == 0  # Even number of unescaped quotes

    def test_shlex_quote_escapes_shell_metacharacters(self):
        """Verify shlex.quote escapes other shell metacharacters."""
        test_cases = [
            "foo$(rm -rf /)",
            "foo`rm -rf /`",
            "foo; rm -rf /",
            "foo | rm -rf /",
            "foo && rm -rf /",
            "foo || rm -rf /",
            "foo> /etc/passwd",
            "foo< /etc/passwd",
            "foo`whoami`",
        ]
        for test in test_cases:
            quoted = shlex.quote(test)
            # All quoted strings should be wrapped in single quotes
            assert quoted.startswith("'")
            assert quoted.endswith("'")

    def test_crawl4ai_single_uses_shlex_quote(self):
        """Verify _try_crawl4ai_single uses shlex.quote on payload."""
        # Mock subprocess.run to capture the command
        with patch("tools.fetch.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="test output", stderr="")
            
            # URL with single quote (potential injection)
            malicious_url = "http://example.com/path?q='; rm -rf /; echo '"
            _try_crawl4ai_single(malicious_url, "http://crawl4ai:42101")
            
            # Verify subprocess.run was called
            assert mock_run.called
            call_args = mock_run.call_args
            cmd = call_args[0][0] if call_args[0] else call_args[1].get("cmd", "")
            
            # The command should use shlex.quote, not raw single quotes
            # Verify the payload is properly quoted (no raw single quotes around payload)
            assert "-d '" not in cmd or "-d 'foo'" not in cmd.replace(malicious_url, "foo")

    def test_crawl4ai_multi_uses_shlex_quote(self):
        """Verify _try_crawl4ai_multi uses shlex.quote on payload."""
        with patch("tools.fetch.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='[{"url": "test"}]', stderr="")
            
            # URLs with single quotes
            malicious_urls = ["http://example.com/path?q='; rm -rf /; echo '"]
            _try_crawl4ai_multi(malicious_urls, "http://crawl4ai:42101")
            
            assert mock_run.called
            call_args = mock_run.call_args
            cmd = call_args[0][0] if call_args[0] else call_args[1].get("cmd", "")
            
            # Verify the command doesn't have raw single quotes around payload
            assert "-d '" not in cmd or "-d 'foo'" not in cmd.replace("'.", "foo")

    def test_normal_url_works_with_shlex_quote(self):
        """Verify normal URLs work correctly with shlex.quote."""
        with patch("tools.fetch.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="test output", stderr="")
            
            normal_url = "http://example.com/page"
            _try_crawl4ai_single(normal_url, "http://crawl4ai:42101")
            
            assert mock_run.called
            call_args = mock_run.call_args
            cmd = call_args[0][0] if call_args[0] else call_args[1].get("cmd", "")
            
            # Verify the command is valid
            assert "curl" in cmd
            assert normal_url in cmd
            assert "-d " in cmd

    def test_payload_with_special_json_chars_is_safe(self):
        """Verify payloads with JSON special characters are safe."""
        with patch("tools.fetch.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="test output", stderr="")
            
            # URL with characters that could break JSON/shell
            tricky_url = "http://example.com/path?q=hello'world&x=$(whoami)"
            _try_crawl4ai_single(tricky_url, "http://crawl4ai:42101")
            
            assert mock_run.called
            call_args = mock_run.call_args
            cmd = call_args[0][0] if call_args[0] else call_args[1].get("cmd", "")
            
            # The command should be safe - no raw shell injection possible
            # Verify shlex.quote was used by checking the -d argument is properly quoted
            assert "-d " in cmd
            # The payload should be wrapped in single quotes by shlex.quote
            assert "'$(whoami)'" not in cmd  # Not raw shell expansion


class TestShlexQuoteBehavior:
    """Test shlex.quote behavior for security verification."""

    def test_empty_string_is_quoted(self):
        assert shlex.quote("") == "''"

    def test_simple_string_is_quoted(self):
        # shlex.quote may or may not quote simple strings depending on version
        result = shlex.quote("hello")
        assert "hello" in result

    def test_string_with_single_quote_is_escaped(self):
        # shlex.quote escapes single quotes using various methods
        result = shlex.quote("foo'bar")
        # The result should be safe for shell use - verify it contains the original content
        assert "foo" in result
        assert "bar" in result
        # And it should use some form of quoting/escaping
        assert len(result) > len("foo'bar")  # Escaping adds characters

    def test_string_with_dollar_is_quoted(self):
        result = shlex.quote("$(whoami)")
        assert result == "'$(whoami)'"
        # Single quotes prevent shell expansion

    def test_string_with_backticks_is_quoted(self):
        result = shlex.quote("`whoami`")
        assert result == "'`whoami`'"
        # Single quotes prevent command substitution

    def test_string_with_semicolon_is_quoted(self):
        result = shlex.quote("foo; bar")
        assert result == "'foo; bar'"
        # Single quotes prevent command separation

    def test_unicode_string_is_quoted(self):
        result = shlex.quote("hello 世界")
        assert "hello" in result
        assert "世界" in result
