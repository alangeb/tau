"""Tests for sandbox.py cache invalidation."""

import pytest
from tools.lib.sandbox import _resolve_whitelist_cache, clear_sandbox_cache, _resolve_whitelist


class TestSandboxCacheClear:
    """Tests for clear_sandbox_cache() function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_sandbox_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        clear_sandbox_cache()

    def test_clear_sandbox_cache_clears_cache(self):
        """clear_sandbox_cache() clears the whitelist cache."""
        # Populate cache
        _resolve_whitelist(["/tmp", "/home"])
        assert len(_resolve_whitelist_cache) > 0

        # Clear cache
        clear_sandbox_cache()
        assert len(_resolve_whitelist_cache) == 0

    def test_clear_sandbox_cache_is_idempotent(self):
        """Calling clear_sandbox_cache() multiple times is safe."""
        clear_sandbox_cache()
        clear_sandbox_cache()  # Should not raise
        assert len(_resolve_whitelist_cache) == 0

    def test_clear_sandbox_cache_allows_refresh(self):
        """After clearing, _resolve_whitelist() repopulates the cache."""
        # First population
        _resolve_whitelist(["/tmp"])
        assert len(_resolve_whitelist_cache) == 1

        # Clear and repopulate
        clear_sandbox_cache()
        _resolve_whitelist(["/home"])
        assert len(_resolve_whitelist_cache) == 1
        assert "/home" in str(_resolve_whitelist_cache)

    def test_cache_keys_are_input_tuples(self):
        """Cache is keyed by input tuple, not resolved paths."""
        _resolve_whitelist(["/tmp", "/home"])
        _resolve_whitelist(["/var", "/usr"])
        assert len(_resolve_whitelist_cache) == 2

        clear_sandbox_cache()
        assert len(_resolve_whitelist_cache) == 0

    def test_clear_sandbox_cache_function_exists(self):
        """clear_sandbox_cache() is importable from tools.lib.sandbox."""
        from tools.lib.sandbox import clear_sandbox_cache as imported_func
        assert callable(imported_func)
