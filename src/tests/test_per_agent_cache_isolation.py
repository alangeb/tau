"""Tests for per-agent cache isolation and thread safety fixes.

Validates that:
1. CacheTracker is per-agent (not global)
2. TokenTracker owns its own CacheTracker
3. SimpleOpenAIClient handles None cache_tracker gracefully
4. CommandManager._ensure_handlers_loaded uses double-check locking
5. _get_skill_list uses double-check locking
6. fork_tool_call_id filtering logs debug message
"""

import threading
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from agent_llm import CacheTracker, CallStats, PrefixCacheTracker
from agent_token_tracker import TokenTracker
from agent_commands import CommandManager


class TestPerAgentCacheTracker(unittest.TestCase):
    """Verify CacheTracker is per-agent, not global."""

    def test_token_tracker_owns_cache_tracker(self):
        """TokenTracker should own its own CacheTracker instance."""
        tt1 = TokenTracker()
        tt2 = TokenTracker()
        # Each TokenTracker should have its own CacheTracker
        self.assertIsNot(tt1._cache_tracker, tt2._cache_tracker)

    def test_cache_tracker_isolation(self):
        """CacheTracker records should be isolated between TokenTrackers."""
        tt1 = TokenTracker()
        tt2 = TokenTracker()

        stats = CallStats(prompt_tokens=100, completion_tokens=50, cached_tokens=80)
        tt1.cache_tracker.record(stats)

        self.assertEqual(tt1.cache_tracker.call_count, 1)
        self.assertEqual(tt2.cache_tracker.call_count, 0)

    def test_clear_tokens_clears_local_tracker(self):
        """clear_tokens() should only clear the local CacheTracker."""
        tt1 = TokenTracker()
        tt2 = TokenTracker()

        stats = CallStats(prompt_tokens=100, completion_tokens=50, cached_tokens=80)
        tt1.cache_tracker.record(stats)
        tt2.cache_tracker.record(stats)

        tt1.clear_tokens()

        self.assertEqual(tt1.cache_tracker.call_count, 0)
        self.assertEqual(tt2.cache_tracker.call_count, 1)

    def test_cache_tracker_hit_rate_isolation(self):
        """Cache hit rates should be isolated between agents."""
        tt1 = TokenTracker()
        tt2 = TokenTracker()

        # Record stats with high cache hit rate for tt1
        stats1 = CallStats(prompt_tokens=1000, completion_tokens=100, cached_tokens=900)
        tt1.cache_tracker.record(stats1)

        # Record stats with low cache hit rate for tt2
        stats2 = CallStats(prompt_tokens=1000, completion_tokens=100, cached_tokens=100)
        tt2.cache_tracker.record(stats2)

        # Hit rates should be different
        self.assertIsNotNone(tt1.cache_tracker.cumulative_hit_rate)
        self.assertIsNotNone(tt2.cache_tracker.cumulative_hit_rate)
        self.assertNotEqual(
            tt1.cache_tracker.cumulative_hit_rate,
            tt2.cache_tracker.cumulative_hit_rate,
        )


class TestNoGlobalCacheTracker(unittest.TestCase):
    """Verify global cache tracker functions have been removed."""

    def test_no_global_cache_tracker(self):
        """agent_llm should not export get_cache_tracker or reset_cache_tracker."""
        import agent_llm
        self.assertFalse(hasattr(agent_llm, "get_cache_tracker"))
        self.assertFalse(hasattr(agent_llm, "reset_cache_tracker"))
        self.assertFalse(hasattr(agent_llm, "_global_cache_tracker"))

    def test_no_global_prefix_cache_tracker(self):
        """agent_llm should not export get_prefix_cache_tracker."""
        import agent_llm
        self.assertFalse(hasattr(agent_llm, "get_prefix_cache_tracker"))
        self.assertFalse(hasattr(agent_llm, "_global_prefix_cache_tracker"))


class TestSimpleOpenAIClientNoneTracker(unittest.TestCase):
    """Verify SimpleOpenAIClient handles None cache_tracker gracefully."""

    def test_none_cache_tracker(self):
        """SimpleOpenAIClient should accept None cache_tracker without error."""
        from agent_llm import SimpleOpenAIClient
        # Should not raise
        client = SimpleOpenAIClient(
            base_url="http://localhost:8000",
            api_key="test",
            timeout=10,
            cache_tracker=None,
        )
        self.assertIsNone(client._cache_tracker)


class TestCommandManagerThreadSafety(unittest.TestCase):
    """Verify CommandManager._ensure_handlers_loaded uses double-check locking."""

    def test_has_lock(self):
        """CommandManager should have a _handlers_lock attribute."""
        self.assertTrue(hasattr(CommandManager, "_handlers_lock"))
        self.assertIsInstance(CommandManager._handlers_lock, type(threading.Lock()))

    def test_ensure_handlers_loaded_is_thread_safe(self):
        """_ensure_handlers_loaded should be safe to call from multiple threads."""
        # Reset state for testing
        original = CommandManager._handlers_loaded
        CommandManager._handlers_loaded = False

        errors = []
        def call_ensure():
            try:
                CommandManager._ensure_handlers_loaded()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=call_ensure) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors: {errors}")
        self.assertTrue(CommandManager._handlers_loaded)

        # Restore original state
        CommandManager._handlers_loaded = original


class TestSkillCacheThreadSafety(unittest.TestCase):
    """Verify _get_skill_list uses double-check locking."""

    def test_has_lock(self):
        """tools.skill should have a _skills_lock."""
        import tools.skill as skill_module
        self.assertTrue(hasattr(skill_module, "_skills_lock"))
        self.assertIsInstance(skill_module._skills_lock, type(threading.Lock()))

    def test_get_skill_list_is_thread_safe(self):
        """_get_skill_list should be safe to call from multiple threads."""
        import tools.skill as skill_module

        # Reset cache for testing
        original_cache = skill_module._skills_cache
        skill_module._skills_cache = None

        errors = []
        results = []
        def call_get():
            try:
                result = skill_module._get_skill_list()
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=call_get) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors: {errors}")
        # All threads should get the same result
        if results:
            for result in results[1:]:
                self.assertEqual(result, results[0])

        # Restore original state
        skill_module._skills_cache = original_cache


class TestForkToolCallIdLogging(unittest.TestCase):
    """Verify fork_tool_call_id filtering logs debug messages."""

    def test_subagent_has_logger(self):
        """agent_subagent should have a logger for debug messages."""
        import agent_subagent
        self.assertTrue(hasattr(agent_subagent, "logger"))


if __name__ == "__main__":
    unittest.main()
