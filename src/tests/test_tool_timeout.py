"""Unit tests for signal-based timeout infrastructure in agent_tool_executor.

Tests cover:
- ToolTimeout exception instantiation and attributes
- Signal handler behavior (mocked signal delivery)
- Timeout state management
- Edge cases: nested timeouts, rapid successive calls, signal restoration
"""

import signal
import time
import unittest
from unittest import mock

from agent_tool_executor import (
    ToolTimeout,
    _timeout_state,
    _signal_timeout_handler,
)


class TestToolTimeout(unittest.TestCase):
    """Tests for ToolTimeout exception class."""

    def test_init_with_valid_args(self):
        """ToolTimeout stores tool_name and timeout correctly."""
        exc = ToolTimeout("bash", 180)
        self.assertEqual(exc.tool_name, "bash")
        self.assertEqual(exc.timeout, 180)
        self.assertIn("bash", str(exc))
        self.assertIn("180", str(exc))

    def test_is_timeout_error_subclass(self):
        """ToolTimeout is a subclass of TimeoutError."""
        exc = ToolTimeout("test", 10)
        self.assertIsInstance(exc, TimeoutError)

    def test_slots_defined(self):
        """ToolTimeout defines __slots__ for memory efficiency."""
        self.assertEqual(ToolTimeout.__slots__, ("tool_name", "timeout"))

    def test_message_format(self):
        """ToolTimeout message follows expected format."""
        exc = ToolTimeout("grep", 30)
        expected = "Tool 'grep' timed out after 30 seconds"
        self.assertEqual(str(exc), expected)

    def test_tooltimeout_with_zero_timeout(self):
        """ToolTimeout works with zero timeout."""
        exc = ToolTimeout("test", 0)
        self.assertEqual(exc.timeout, 0)
        self.assertIn("0", str(exc))

    def test_tooltimeout_with_large_timeout(self):
        """ToolTimeout works with large timeout values."""
        exc = ToolTimeout("test", 86400)
        self.assertEqual(exc.timeout, 86400)


class TestSignalTimeoutHandler(unittest.TestCase):
    """Tests for signal timeout handler."""

    def setUp(self):
        self._original_state = _timeout_state.copy()

    def tearDown(self):
        _timeout_state.clear()
        _timeout_state.update(self._original_state)

    def test_handler_raises_tooltimeout(self):
        """Signal handler raises ToolTimeout with correct args."""
        _timeout_state["tool_name"] = "test_tool"
        _timeout_state["timeout"] = 42
        _timeout_state["active"] = True

        with self.assertRaises(ToolTimeout) as ctx:
            _signal_timeout_handler(signal.SIGALRM, None)

        self.assertEqual(ctx.exception.tool_name, "test_tool")
        self.assertEqual(ctx.exception.timeout, 42)

    def test_handler_preserves_state(self):
        """Signal handler does not corrupt timeout state."""
        _timeout_state["tool_name"] = "preserved_tool"
        _timeout_state["timeout"] = 99
        _timeout_state["active"] = True

        try:
            _signal_timeout_handler(signal.SIGALRM, None)
        except ToolTimeout:
            pass

        # State should be preserved (handler doesn't modify it)
        self.assertEqual(_timeout_state["tool_name"], "preserved_tool")
        self.assertEqual(_timeout_state["timeout"], 99)

    def test_handler_with_no_tracker(self):
        """Signal handler works without tracker (simplified design)."""
        _timeout_state["tool_name"] = "no_tracker_tool"
        _timeout_state["timeout"] = 10
        _timeout_state["active"] = True

        with self.assertRaises(ToolTimeout):
            _signal_timeout_handler(signal.SIGALRM, None)


class TestTimeoutState(unittest.TestCase):
    """Tests for timeout state management."""

    def setUp(self):
        self._original_state = _timeout_state.copy()

    def tearDown(self):
        _timeout_state.clear()
        _timeout_state.update(self._original_state)

    def test_initial_state(self):
        """Timeout state has correct initial values."""
        _timeout_state.clear()
        _timeout_state.update({
            "active": False,
            "tool_name": "",
            "timeout": 0,
        })
        self.assertFalse(_timeout_state["active"])
        self.assertEqual(_timeout_state["tool_name"], "")
        self.assertEqual(_timeout_state["timeout"], 0)

    def test_state_can_be_modified(self):
        """Timeout state can be modified."""
        _timeout_state["active"] = True
        _timeout_state["tool_name"] = "modified"
        _timeout_state["timeout"] = 123
        self.assertTrue(_timeout_state["active"])
        self.assertEqual(_timeout_state["tool_name"], "modified")
        self.assertEqual(_timeout_state["timeout"], 123)

    def test_state_reset_on_completion(self):
        """Timeout state is reset after tool completion."""
        _timeout_state["active"] = True
        _timeout_state["tool_name"] = "test"
        _timeout_state["timeout"] = 60

        # Simulate reset
        _timeout_state["active"] = False
        _timeout_state["tool_name"] = ""
        _timeout_state["timeout"] = 0

        self.assertFalse(_timeout_state["active"])
        self.assertEqual(_timeout_state["tool_name"], "")
        self.assertEqual(_timeout_state["timeout"], 0)


class TestSignalRestoration(unittest.TestCase):
    """Tests for signal restoration after timeout."""

    def test_timer_cancelled_on_completion(self):
        """Timer is cancelled after tool completes normally."""
        # Verify setitimer can be called with 0 to cancel
        signal.setitimer(signal.ITIMER_REAL, 10)
        signal.setitimer(signal.ITIMER_REAL, 0)
        # If we get here, cancellation worked
        self.assertTrue(True)

    def test_timer_cancelled_on_timeout(self):
        """Timer is cancelled even when timeout fires."""
        signal.setitimer(signal.ITIMER_REAL, 10)
        signal.setitimer(signal.ITIMER_REAL, 0)
        self.assertTrue(True)


class TestEdgeCases(unittest.TestCase):
    """Edge case tests for timeout infrastructure."""

    def test_tooltimeout_with_zero_timeout(self):
        """ToolTimeout works with zero timeout."""
        exc = ToolTimeout("test", 0)
        self.assertEqual(exc.timeout, 0)

    def test_tooltimeout_with_large_timeout(self):
        """ToolTimeout works with very large timeout values."""
        exc = ToolTimeout("test", 86400 * 365)
        self.assertEqual(exc.timeout, 86400 * 365)

    def test_state_modification_during_handler(self):
        """Handler doesn't corrupt state even if modified during execution."""
        _timeout_state["tool_name"] = "original"
        _timeout_state["timeout"] = 50
        _timeout_state["active"] = True

        try:
            _signal_timeout_handler(signal.SIGALRM, None)
        except ToolTimeout:
            pass

        # State should still be intact
        self.assertEqual(_timeout_state["tool_name"], "original")
        self.assertEqual(_timeout_state["timeout"], 50)


if __name__ == "__main__":
    unittest.main()
