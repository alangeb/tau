"""Tests for ToolFilter.denied_message feature.

Verifies that blocked tool invocations produce instructive denial messages
with available tool alternatives.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_core import ToolFilter


class TestToolFilterDeniedMessage:
    """Test suite for ToolFilter denial message formatting."""

    # -- Default message tests --

    def test_default_denied_message(self):
        """Default denied message includes tool name, available tools, and instruction."""
        tf = ToolFilter(allowlist={"read", "grep"})
        msg = tf.format_denied("write_file", ["read", "grep", "info"])

        assert "write_file" in msg
        assert "read" in msg
        assert "grep" in msg
        assert "restricted" in msg
        assert "Reformulate" in msg

    def test_default_denied_message_sorted_tools(self):
        """Available tools in the default message are sorted alphabetically."""
        tf = ToolFilter()
        msg = tf.format_denied("bad_tool", ["zebra", "alpha", "middleware"])

        alpha_idx = msg.index("alpha")
        mid_idx = msg.index("middleware")
        zebra_idx = msg.index("zebra")
        assert alpha_idx < mid_idx < zebra_idx

    # -- Custom message tests --

    def test_custom_denied_message(self):
        """Custom denied_message template is used with placeholders filled."""
        tf = ToolFilter(
            allowlist={"read"},
            denied_message=(
                "DO NOT use {tool_name}. You are read-only. " "Use: {available_tools}."
            ),
        )
        msg = tf.format_denied("write_file", ["read", "grep"])

        assert "DO NOT use write_file" in msg
        assert "read-only" in msg
        assert "read" in msg
        assert "grep" in msg

    def test_custom_denied_message_no_placeholders(self):
        """Custom message without placeholders works as-is."""
        tf = ToolFilter(
            denied_message="That tool is not available. Try something else."
        )
        msg = tf.format_denied("anything", ["read"])

        assert msg == "That tool is not available. Try something else."

    # -- Edge cases --

    def test_empty_available_tools(self):
        """Denial still works when no tools are available."""
        tf = ToolFilter(allowlist=set())
        msg = tf.format_denied("read", [])

        assert "read" in msg
        assert "restricted" in msg
        assert "Available tools: " in msg

    def test_should_include_unchanged(self):
        """denied_message field does not affect should_include behavior."""
        tf = ToolFilter(
            allowlist={"read", "grep"},
            denied_message="Custom: {tool_name} blocked.",
        )
        assert tf.should_include("read") is True
        assert tf.should_include("write_file") is False
        assert tf.should_include("grep") is True

    def test_no_filter_allows_all(self):
        """Default ToolFilter() allows everything, denied path never hit."""
        tf = ToolFilter()
        assert tf.should_include("anything") is True

    def test_malformed_template_falls_back_to_default(self):
        """Unknown placeholder in template falls back to default message."""
        tf = ToolFilter(
            allowlist={"read"},
            denied_message="Tool {tool_name} blocked. Use {foo} instead.",
        )
        msg = tf.format_denied("write_file", ["read"])
        # Must NOT raise KeyError — must fall back to default
        assert "write_file" in msg
        assert "restricted" in msg
        assert "Reformulate" in msg
        assert "foo" not in msg

    # -- Integration with execute_tool_call --

    def test_execute_tool_call_uses_denied_message(self):
        """execute_tool_call returns the formatted denial for blocked tools."""
        from agent_tool_executor import execute_tool_call

        agent = MagicMock()
        agent.tool_filter = ToolFilter(
            allowlist={"read"},
            denied_message="BLOCKED: {tool_name}. Use {available_tools}.",
        )
        agent.available_tool_names = ["read", "grep", "write_file"]
        agent.loop_detector = MagicMock()
        agent.loop_detector.detect_tool_loop.return_value = None

        tc = {
            "id": "test-1",
            "name": "write_file",
            "args": "{}",
        }

        result = execute_tool_call(tc, agent)
        assert "BLOCKED: write_file" in result
        assert "read" in result
        # Only "read" appears because grep/write_file are NOT in the allowlist,
        # so they are filtered out of the available_tools list before formatting
        assert "grep" not in result

    def test_execute_tool_call_default_denied_message(self):
        """Default denial message is used when denied_message is None."""
        from agent_tool_executor import execute_tool_call

        agent = MagicMock()
        agent.tool_filter = ToolFilter(allowlist={"read"})
        agent.available_tool_names = ["read", "grep", "write_file"]
        agent.loop_detector = MagicMock()
        agent.loop_detector.detect_tool_loop.return_value = None

        tc = {
            "id": "test-2",
            "name": "write_file",
            "args": "{}",
        }

        result = execute_tool_call(tc, agent)
        assert "write_file" in result
        assert "restricted" in result
        assert "Reformulate" in result

    def test_execute_tool_call_allowed_tool_passes_through(self):
        """Allowed tools are not blocked by the filter."""
        from agent_tool_executor import execute_tool_call

        agent = MagicMock()
        agent.tool_filter = ToolFilter(allowlist={"read"})
        agent.available_tool_names = ["read", "grep"]
        agent.loop_detector = MagicMock()
        agent.loop_detector.detect_tool_loop.return_value = None

        # "read" is allowed — should not hit the denial path
        tc = {
            "id": "test-3",
            "name": "read",
            "args": "{}",
        }

        mock_entry = MagicMock()
        mock_entry.run = MagicMock(return_value="ok")
        mock_entry.max_size = 16384
        with patch("agent_tool_executor.TOOLS", {"read": mock_entry}):
            result = execute_tool_call(tc, agent)
            assert "restricted" not in result
            assert "not available" not in result
