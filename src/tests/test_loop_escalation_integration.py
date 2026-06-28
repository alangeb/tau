"""Integration tests for LoopEscalationManager in agent_loop_escalation.py.

Tests the escalation manager that orchestrates loop recovery:
- Level 4: Sets force_end_turn and returns False
- Level 3: Injects context, resets detector
- Level 2: Injects context with suggestions
- Level 1: Informational warning only
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


def _make_manager(escalation_level=0, total_warnings=0):
    """Build a LoopEscalationManager with controllable escalation state."""
    detector = LoopDetector(
        repeat_threshold=1,
        warn_threshold=1,
        inject_threshold=1,
        force_think_threshold=1,
        end_turn_threshold=1,
    )
    detector.escalation_level = escalation_level
    detector.total_warnings = total_warnings
    detector.get_escalation_info = MagicMock(return_value={
        "escalation_level": escalation_level,
        "total_warnings": total_warnings,
    })
    context = TauContext()
    context.set_system("You are a helpful assistant.")
    agent = MagicMock()
    return LoopEscalationManager(detector, ReflectionScheduler(ReflectionConfig()), context, agent)


class TestHandleLoopEscalationLevel4:
    """Test Level 4 (nuclear: force_end_turn) escalation."""

    @patch("agent_loop_escalation.loop_warning")
    def test_level_4_sets_force_end_turn(self, mock_warn):
        """Level 4 sets force_end_turn and returns False."""
        mgr = _make_manager(escalation_level=4, total_warnings=15)
        result = mgr.handle_loop_escalation()

        assert result is False
        assert mgr._agent.force_end_turn is not None
        assert "15" in mgr._agent.force_end_turn
        mock_warn.assert_called_once()

    @patch("agent_loop_escalation.loop_warning")
    def test_level_4_does_not_append_to_context(self, mock_warn):
        """Level 4 does NOT append to context (caller handles it)."""
        mgr = _make_manager(escalation_level=4, total_warnings=15)
        mgr._context.append_assistant = MagicMock()
        mgr.handle_loop_escalation()

        # Verify context.append_assistant was NOT called
        mgr._context.append_assistant.assert_not_called()


class TestHandleLoopEscalationLevel3:
    """Test Level 3 (forced think mode) escalation."""

    @patch("agent_loop_escalation.loop_warning")
    @patch("agent_loop_escalation.get_last_real_user_prompt", return_value="test prompt")
    def test_level_3_injects_context_and_resets_detector(self, mock_prompt, mock_warn):
        """Level 3 injects assistant + synthetic user messages and resets loop detector."""
        mgr = _make_manager(escalation_level=3, total_warnings=11)
        mgr._loop_detector.reset = MagicMock()
        result = mgr.handle_loop_escalation()

        assert result is True
        mock_warn.assert_called_once()
        mgr._loop_detector.reset.assert_called_once()

        # Verify synthetic user message was injected
        messages = mgr._context.get_messages()
        # Find the last synthetic user message
        synthetic_msgs = [m for m in messages if m.get("role") == "user" and is_synthetic_message(m)]
        assert len(synthetic_msgs) >= 1

    @patch("agent_loop_escalation.loop_warning")
    @patch("agent_loop_escalation.get_last_real_user_prompt", return_value="test prompt")
    def test_level_3_injects_context(self, mock_prompt, mock_warn):
        """Level 3 injects assistant + synthetic user messages to context."""
        mgr = _make_manager(escalation_level=3, total_warnings=11)
        mgr.handle_loop_escalation()

        messages = mgr._context.get_messages()
        # Find synthetic user messages
        synthetic_msgs = [m for m in messages if m.get("role") == "user" and is_synthetic_message(m)]
        assert len(synthetic_msgs) >= 1

        # Check that the message is a properly structured synthetic escalation message
        last_synthetic = synthetic_msgs[-1]
        assert is_synthetic_message(last_synthetic)
        assert "escalation" in last_synthetic["content"]


class TestHandleLoopEscalationLevel2:
    """Test Level 2 (context injection) escalation."""

    @patch("agent_loop_escalation.loop_warning")
    @patch("agent_loop_escalation.get_last_real_user_prompt", return_value="test prompt")
    def test_level_2_injects_context(self, mock_prompt, mock_warn):
        """Level 2 injects assistant + synthetic user messages."""
        mgr = _make_manager(escalation_level=2, total_warnings=7)
        mgr.handle_loop_escalation()

        messages = mgr._context.get_messages()
        # Find synthetic user messages
        synthetic_msgs = [m for m in messages if m.get("role") == "user" and is_synthetic_message(m)]
        assert len(synthetic_msgs) >= 1
        mock_warn.assert_called_once()

    @patch("agent_loop_escalation.loop_warning")
    @patch("agent_loop_escalation.get_last_real_user_prompt", return_value="my original task description")
    def test_level_2_includes_original_prompt(self, mock_prompt, mock_warn):
        """Level 2 injection includes original user prompt."""
        mgr = _make_manager(escalation_level=2, total_warnings=7)
        mgr.handle_loop_escalation()

        messages = mgr._context.get_messages()
        # Find synthetic user messages containing the original prompt
        synthetic_msgs = [m for m in messages if m.get("role") == "user" and is_synthetic_message(m)]
        assert len(synthetic_msgs) >= 1

        last_synthetic = synthetic_msgs[-1]
        assert "my original task description" in last_synthetic["content"]


class TestHandleLoopEscalationLevel1:
    """Test Level 1 (informational warning) escalation."""

    @patch("agent_loop_escalation.loop_warning")
    def test_level_1_only_warns(self, mock_warn):
        """Level 1 only displays warning, no context injection."""
        mgr = _make_manager(escalation_level=1, total_warnings=3)
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
        mgr = _make_manager(escalation_level=0, total_warnings=0)
        result = mgr.handle_loop_escalation()

        assert result is True
