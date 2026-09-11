"""Tests for get_all_tools() caching in agent_core.py."""

from __future__ import annotations

import inspect


class TestGetAllToolsCache:
    """Test that get_all_tools() caches its result correctly."""

    def test_get_all_tools_has_cache_check(self):
        """Verify get_all_tools() has cache check logic."""
        import agent_core

        source = inspect.getsource(agent_core.TauErgon.get_all_tools)
        assert "_cached_tools" in source, "get_all_tools() should reference _cached_tools"
        assert "is not None" in source or "is None" in source, "Should check cache validity"

    def test_get_all_tools_caches_result(self):
        """Verify get_all_tools() caches its result."""
        import agent_core

        source = inspect.getsource(agent_core.TauErgon.get_all_tools)
        assert "self._cached_tools = " in source, "Should assign to _cached_tools"

    def test_init_subsystems_initializes_cached_tools(self):
        """Verify _init_subsystems initializes _cached_tools."""
        import agent_core

        source = inspect.getsource(agent_core.TauErgon._init_subsystems)
        assert "_cached_tools" in source, "_init_subsystems should initialize _cached_tools"

    def test_cached_tools_type_annotation(self):
        """Verify _cached_tools has correct type annotation."""
        import agent_core

        source = inspect.getsource(agent_core.TauErgon._init_subsystems)
        assert "_cached_tools: list[dict] | None = None" in source, \
            "_cached_tools should be typed as list[dict] | None = None"

    def test_get_all_tools_returns_same_object_on_repeated_calls(self):
        """Verify get_all_tools() returns the same object on repeated calls."""
        from agent_core import TauErgon

        # Create a minimal mock agent using object.__new__ to bypass __init__
        agent = object.__new__(TauErgon)
        agent.available_tool_names = ["info"]
        agent._cached_tools = None  # Initialize cache

        # Mock TOOLS to return a simple tool entry
        from unittest.mock import MagicMock
        mock_entry = MagicMock()
        mock_entry.description = "test tool"
        mock_entry.get_schema.return_value = {"type": "object", "properties": {}, "required": []}

        import agent_core
        original_tools = agent_core.TOOLS
        agent_core.TOOLS = {"info": mock_entry}

        try:
            # First call should compute and cache
            result1 = agent.get_all_tools()
            assert agent._cached_tools is not None, "Cache should be populated"

            # Second call should return cached result (same object)
            result2 = agent.get_all_tools()
            assert result1 is result2, "Should return same cached object"

            # Verify structure
            assert isinstance(result1, list), "Result should be a list"
            assert len(result1) == 1, "Should have one tool"
            assert result1[0]["type"] == "function", "Tool should have type 'function'"
            assert result1[0]["function"]["name"] == "info", "Tool name should be 'info'"
        finally:
            agent_core.TOOLS = original_tools


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
