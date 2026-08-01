"""Tests for delegate command.

Tests the delegate command's loop mechanics, tool restrictions,
and exit conditions.
"""

import pytest
from unittest.mock import MagicMock, patch

from agent_context import TauContext
from agent_tool_filter import ToolFilter
from commands.delegate import (
    _ALLOWED_DELEGATE_TOOLS,
    DELEGATE_INSTRUCTIONS,
    NAME,
    DESCRIPTION,
    run,
)


class TestDelegateMetadata:
    """Test delegate command metadata."""

    def test_name(self):
        """Delegate command has correct name."""
        assert NAME == "delegate"

    def test_description(self):
        """Delegate command has meaningful description."""
        assert "orchestrator" in DESCRIPTION.lower()
        assert "delegate" in DESCRIPTION.lower()

    def test_allowed_tools_not_empty(self):
        """Delegate mode has allowed tools defined."""
        assert len(_ALLOWED_DELEGATE_TOOLS) > 0

    def test_delegation_tools_allowed(self):
        """fork and subagent are allowed in delegate mode."""
        assert "fork" in _ALLOWED_DELEGATE_TOOLS
        assert "subagent" in _ALLOWED_DELEGATE_TOOLS

    def test_end_turn_allowed(self):
        """end_turn is allowed in delegate mode (needed for EOT)."""
        assert "end_turn" in _ALLOWED_DELEGATE_TOOLS

    def test_write_tools_blocked(self):
        """Write tools are NOT allowed in delegate mode."""
        assert "file_write" not in _ALLOWED_DELEGATE_TOOLS
        assert "bash" not in _ALLOWED_DELEGATE_TOOLS
        assert "background_run" not in _ALLOWED_DELEGATE_TOOLS

    def test_read_tools_allowed(self):
        """Read/analysis tools are allowed in delegate mode."""
        assert "file_read" in _ALLOWED_DELEGATE_TOOLS
        assert "glob" in _ALLOWED_DELEGATE_TOOLS
        assert "grep" in _ALLOWED_DELEGATE_TOOLS
        assert "pyscan" in _ALLOWED_DELEGATE_TOOLS


class TestDelegateInstructions:
    """Test delegate instructions content."""

    def test_instructions_mention_orchestrator(self):
        """Instructions mention orchestrator role."""
        assert "orchestrator" in DELEGATE_INSTRUCTIONS.lower()

    def test_instructions_mention_no_work(self):
        """Instructions say delegate should not do work itself."""
        assert "do NOT do work" in DELEGATE_INSTRUCTIONS or "do not do work" in DELEGATE_INSTRUCTIONS.lower()

    def test_instructions_mention_fork(self):
        """Instructions mention fork tool."""
        assert "fork" in DELEGATE_INSTRUCTIONS

    def test_instructions_mention_subagent(self):
        """Instructions mention subagent tool."""
        assert "subagent" in DELEGATE_INSTRUCTIONS


class TestDelegateRun:
    """Test delegate command execution."""

    def test_run_with_help_flag(self):
        """Run with help flag prints usage."""
        agent = MagicMock()
        with patch("commands.delegate.echo") as mock_echo:
            run(agent, ["help"])
        mock_echo.assert_called()

    def test_run_with_no_args(self):
        """Run with no args prints usage."""
        agent = MagicMock()
        with patch("commands.delegate.echo") as mock_echo:
            run(agent, [])
        mock_echo.assert_called()

    def test_run_sets_tool_filter(self):
        """Run sets tool filter to delegate mode."""
        agent = MagicMock()
        agent.tool_filter = None
        agent.invoke_with_tools.return_value = "Done with task."

        with patch("commands.delegate.blank_line"), \
             patch("commands.delegate.status"):
            run(agent, ["test task"])

        # Verify tool filter was set (and restored in finally)
        assert agent.tool_filter is None  # Restored in finally

    def test_run_calls_invoke_with_tools(self):
        """Run calls invoke_with_tools with task and instructions."""
        agent = MagicMock()
        agent.tool_filter = None
        agent.invoke_with_tools.return_value = "Done with task."

        with patch("commands.delegate.blank_line"), \
             patch("commands.delegate.status"):
            run(agent, ["test task"])

        # Verify invoke_with_tools was called
        assert agent.invoke_with_tools.called
        call_args = agent.invoke_with_tools.call_args_list[0][0][0]
        assert "test task" in call_args
        assert "DELEGATE MODE" in call_args

    def test_run_exits_on_normal_response(self):
        """Run exits when invoke_with_tools returns normal response."""
        agent = MagicMock()
        agent.tool_filter = None
        agent.invoke_with_tools.return_value = "Task completed successfully."

        with patch("commands.delegate.blank_line"), \
             patch("commands.delegate.status"):
            run(agent, ["test task"])

        # Should only be called once (first turn), not in continue loop
        assert agent.invoke_with_tools.call_count == 1

    def test_run_exits_on_error_response(self):
        """Run exits when invoke_with_tools returns error."""
        agent = MagicMock()
        agent.tool_filter = None
        agent.invoke_with_tools.return_value = "Error: Failed to invoke model - timeout"

        with patch("commands.delegate.blank_line"), \
             patch("commands.delegate.status"):
            run(agent, ["test task"])

        # Should only be called once (error exits loop)
        assert agent.invoke_with_tools.call_count == 1

    def test_run_continues_on_none_response(self):
        """Run continues loop when invoke_with_tools returns None (interrupted)."""
        agent = MagicMock()
        agent.tool_filter = None
        # First call returns None (interrupted), second call returns normal response
        agent.invoke_with_tools.side_effect = [
            None,  # Interrupted, continues
            "Task completed after retry.",  # Normal, exits
        ]

        with patch("commands.delegate.blank_line"), \
             patch("commands.delegate.status"):
            run(agent, ["test task"])

        # Should be called twice (first None, then normal)
        assert agent.invoke_with_tools.call_count == 2

    def test_run_resets_force_end_turn(self):
        """Run resets force_end_turn in finally block."""
        agent = MagicMock()
        agent.tool_filter = None
        agent.force_end_turn = "some value"
        agent.invoke_with_tools.return_value = "Done."

        with patch("commands.delegate.blank_line"), \
             patch("commands.delegate.status"):
            run(agent, ["test task"])

        # Verify force_end_turn was reset
        assert agent.force_end_turn is None

    def test_run_restores_original_filter(self):
        """Run restores original tool filter in finally block."""
        original = ToolFilter(allowlist={"test"})
        agent = MagicMock()
        agent.tool_filter = original
        agent.invoke_with_tools.return_value = "Done."

        with patch("commands.delegate.blank_line"), \
             patch("commands.delegate.status"):
            run(agent, ["test task"])

        # Verify original filter was restored
        assert agent.tool_filter is original


class TestDelegateLoopCondition:
    """Test delegate loop exit conditions."""

    def test_loop_exits_on_empty_response(self):
        """Loop exits when invoke_with_tools returns empty string."""
        agent = MagicMock()
        agent.tool_filter = None
        agent.invoke_with_tools.return_value = ""

        with patch("commands.delegate.blank_line"), \
             patch("commands.delegate.status"):
            run(agent, ["test task"])

        # Should only be called once (empty string exits loop)
        assert agent.invoke_with_tools.call_count == 1

    def test_loop_exits_on_normal_response(self):
        """Loop exits when invoke_with_tools returns normal response."""
        agent = MagicMock()
        agent.tool_filter = None
        agent.invoke_with_tools.return_value = "Task completed."

        with patch("commands.delegate.blank_line"), \
             patch("commands.delegate.status"):
            run(agent, ["test task"])

        # Should only be called once (normal response exits loop)
        assert agent.invoke_with_tools.call_count == 1

    def test_loop_continues_on_none_then_exits(self):
        """Loop continues on None, exits on normal response."""
        agent = MagicMock()
        agent.tool_filter = None
        agent.invoke_with_tools.side_effect = [
            None,  # Interrupted, continues
            "Task completed.",  # Normal, exits
        ]

        with patch("commands.delegate.blank_line"), \
             patch("commands.delegate.status"):
            run(agent, ["test task"])

        # Should be called twice
        assert agent.invoke_with_tools.call_count == 2

    def test_continue_prompt_includes_instructions(self):
        """Continue loop injects prompt with instructions."""
        agent = MagicMock()
        agent.tool_filter = None
        agent.invoke_with_tools.side_effect = [
            None,  # Interrupted, continues
            "Done.",  # Normal, exits
        ]

        with patch("commands.delegate.blank_line"), \
             patch("commands.delegate.status"):
            run(agent, ["my task"])

        # Check second call has "Continue TASK" and instructions
        second_call = agent.invoke_with_tools.call_args_list[1][0][0]
        assert "Continue TASK" in second_call
        assert "DELEGATE MODE" in second_call

    def test_loop_respects_max_iterations(self):
        """Loop respects max iteration limit (safety)."""
        agent = MagicMock()
        agent.tool_filter = None
        # Always return None (simulating continuous interrupts)
        agent.invoke_with_tools.return_value = None

        with patch("commands.delegate.blank_line"), \
             patch("commands.delegate.status"):
            run(agent, ["test task"])

        # Should be called max_iterations + 1 times (first call + max continues)
        # max_iterations = 10, so total = 11
        assert agent.invoke_with_tools.call_count <= 11