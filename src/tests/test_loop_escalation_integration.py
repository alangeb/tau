"""Integration tests for LoopEscalationManager in agent_loop_escalation.py.

Tests the escalation manager that orchestrates loop recovery:
- Level 5 (warnings 15+): Sets force_end_turn and returns False
- Level 4 (warnings 12-14): Injects assistant + synthetic think result
- Level 3 (warnings 9-11): Injects assistant + synthetic user questions
- Level 2 (warnings 6-8): Injects assistant + synthetic think result
- Level 1 (warnings 3-5): Informational warning only

System-initiated tool calls (synthetic think/end_turn) use system_call=True
to avoid polluting loop detection patterns.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import MagicMock, patch

from agent_loop_detect import LoopDetector
from agent_reflection import ReflectionScheduler, ReflectionConfig
from agent_context import TauContext
from agent_message_utils import is_synthetic_message
from agent_loop_escalation import LoopEscalationManager


def _make_manager(escalation_level=0, total_warnings=0, tool_warnings=None, restricted_nesting=False):
    """Build a LoopEscalationManager with controllable escalation state."""
    detector = LoopDetector(repeat_threshold=1)
    detector.escalation_level = escalation_level
    detector.total_warnings = total_warnings
    detector.tool_warnings = tool_warnings or {}
    detector.get_escalation_info = MagicMock(return_value={
        "escalation_level": escalation_level,
        "total_warnings": total_warnings,
        "tool_warnings": tool_warnings or {},
    })
    context = TauContext()
    context.set_system("You are a helpful assistant.")
    agent = MagicMock()
    agent._is_restricted_nesting.return_value = restricted_nesting
    agent.last_substantive_response = None
    return LoopEscalationManager(detector, ReflectionScheduler(ReflectionConfig()), context, agent)


class TestHandleLoopEscalationLevel5:
    """Test Level 5 (termination: force_end_turn) escalation."""

    @patch("agent_loop_escalation.loop_warning")
    def test_level_5_sets_force_end_turn(self, mock_warn):
        """Level 5 sets force_end_turn and returns False."""
        mgr = _make_manager(escalation_level=5, total_warnings=15, tool_warnings={"bash": 10})
        result = mgr.handle_loop_escalation()

        assert result is False
        assert mgr._agent.force_end_turn is not None
        assert "15" in mgr._agent.force_end_turn
        mock_warn.assert_called_once()

    @patch("agent_loop_escalation.loop_warning")
    def test_level_5_does_not_append_to_context(self, mock_warn):
        """Level 5 does NOT append to context (caller handles it)."""
        mgr = _make_manager(escalation_level=5, total_warnings=15, tool_warnings={"bash": 10})
        mgr._context.append_assistant = MagicMock()
        mgr.handle_loop_escalation()

        # Verify context.append_assistant was NOT called
        mgr._context.append_assistant.assert_not_called()


class TestHandleLoopEscalationLevel4:
    """Test Level 4 (forced analysis) escalation."""

    @patch("agent_loop_escalation.loop_warning")
    def test_level_4_injects_assistant_tool(self, mock_warn):
        """Level 4 injects assistant + synthetic think result."""
        mgr = _make_manager(escalation_level=4, total_warnings=12, tool_warnings={"bash": 10})
        result = mgr.handle_loop_escalation()

        assert result is True
        mock_warn.assert_called_once()

        # Verify assistant message was injected with tool_calls
        messages = mgr._context.get_messages()
        assistant_msgs = [m for m in messages if m.get("role") == "assistant" and m.get("tool_calls")]
        assert len(assistant_msgs) >= 1

        # Verify tool result was injected
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        assert len(tool_msgs) >= 1


class TestHandleLoopEscalationLevel3:
    """Test Level 3 (guided introspection) escalation."""

    @patch("agent_loop_escalation.loop_warning")
    @patch("agent_loop_escalation.get_last_real_user_prompt", return_value="test prompt")
    def test_level_3_injects_assistant_user(self, mock_prompt, mock_warn):
        """Level 3 injects assistant + synthetic user questions."""
        mgr = _make_manager(escalation_level=3, total_warnings=9, tool_warnings={"bash": 10})
        result = mgr.handle_loop_escalation()

        assert result is True
        mock_warn.assert_called_once()

        # Verify synthetic user message was injected
        messages = mgr._context.get_messages()
        synthetic_msgs = [m for m in messages if m.get("role") == "user" and is_synthetic_message(m)]
        assert len(synthetic_msgs) >= 1

    @patch("agent_loop_escalation.loop_warning")
    @patch("agent_loop_escalation.get_last_real_user_prompt", return_value="my original task")
    def test_level_3_includes_original_prompt(self, mock_prompt, mock_warn):
        """Level 3 injection includes original user prompt."""
        mgr = _make_manager(escalation_level=3, total_warnings=9, tool_warnings={"bash": 10})
        mgr.handle_loop_escalation()

        messages = mgr._context.get_messages()
        synthetic_msgs = [m for m in messages if m.get("role") == "user" and is_synthetic_message(m)]
        assert len(synthetic_msgs) >= 1

        last_synthetic = synthetic_msgs[-1]
        assert "my original task" in last_synthetic["content"]


class TestHandleLoopEscalationLevel2:
    """Test Level 2 (simulated self-reflection) escalation."""

    @patch("agent_loop_escalation.loop_warning")
    def test_level_2_injects_assistant_tool(self, mock_warn):
        """Level 2 injects assistant + synthetic think result."""
        mgr = _make_manager(escalation_level=2, total_warnings=6, tool_warnings={"bash": 10})
        result = mgr.handle_loop_escalation()

        assert result is True
        mock_warn.assert_called_once()

        # Verify assistant message was injected with tool_calls
        messages = mgr._context.get_messages()
        assistant_msgs = [m for m in messages if m.get("role") == "assistant" and m.get("tool_calls")]
        assert len(assistant_msgs) >= 1

        # Verify tool result was injected
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        assert len(tool_msgs) >= 1


class TestHandleLoopEscalationLevel1:
    """Test Level 1 (informational warning) escalation."""

    @patch("agent_loop_escalation.loop_warning")
    def test_level_1_only_warns(self, mock_warn):
        """Level 1 only displays warning, no context injection."""
        mgr = _make_manager(escalation_level=1, total_warnings=3, tool_warnings={"bash": 10})
        result = mgr.handle_loop_escalation()

        assert result is True
        mock_warn.assert_called_once()

        # Verify no messages were added (context should only have system message)
        messages = mgr._context.get_messages()
        # Filter out system message
        non_system = [m for m in messages if m.get("role") != "system"]
        assert len(non_system) == 0


class TestHandleLoopEscalationLevel0:
    """Test Level 0 (normal operation) - no escalation."""

    def test_level_0_no_action(self):
        """Level 0 returns True with no side effects."""
        mgr = _make_manager(escalation_level=0, total_warnings=0, tool_warnings={})
        result = mgr.handle_loop_escalation()

        assert result is True


class TestHandleLoopEscalationRestrictedNesting:
    """Test restricted nesting (T/K) escalation behavior."""

    @patch("agent_loop_escalation.loop_warning")
    def test_level_1_aborts_for_restricted_nesting(self, mock_warn):
        """Level 1 aborts immediately for T/K nesting types."""
        mgr = _make_manager(
            escalation_level=1,
            total_warnings=3,
            tool_warnings={"bash": 3},
            restricted_nesting=True,
        )
        mgr._agent.last_substantive_response = "last response"
        result = mgr.handle_loop_escalation()

        assert result is False
        assert mgr._agent.force_end_turn is not None
        assert "3" in mgr._agent.force_end_turn
        assert "restricted" in mgr._agent.force_end_turn.lower() or "loop" in mgr._agent.force_end_turn.lower()

    @patch("agent_loop_escalation.loop_warning")
    def test_level_2_aborts_for_restricted_nesting(self, mock_warn):
        """Level 2 aborts immediately for T/K nesting types."""
        mgr = _make_manager(
            escalation_level=2,
            total_warnings=6,
            tool_warnings={"bash": 6},
            restricted_nesting=True,
        )
        mgr._agent.last_substantive_response = "last response"
        result = mgr.handle_loop_escalation()

        assert result is False
        assert mgr._agent.force_end_turn is not None

    @patch("agent_loop_escalation.loop_warning")
    def test_level_1_normal_for_non_restricted_nesting(self, mock_warn):
        """Level 1 only warns for non-restricted nesting (S/F)."""
        mgr = _make_manager(
            escalation_level=1,
            total_warnings=3,
            tool_warnings={"bash": 3},
            restricted_nesting=False,
        )
        mgr._agent.force_end_turn = None  # Reset to None
        result = mgr.handle_loop_escalation()

        assert result is True
        assert mgr._agent.force_end_turn is None
