"""Tests for loop escalation system.

Tests cover:
- Cumulative tracking (total_warnings, tool_warnings)
- Escalation level computation
- Escalating warning messages
- Context compliance for injection sequences
- Think-forcing via ToolFilter
- Synthetic loop simulation
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from agent_loop_detect import LoopDetector, WARNING_LEVEL_1, WARNING_LEVEL_2, WARNING_LEVEL_3
from agent_context import TauContext
from agent_core import ToolFilter


class TestCumulativeTracking:
    """Test cumulative warning tracking in LoopDetector."""

    def test_total_warnings_increments(self):
        """total_warnings increments on each detected loop."""
        detector = LoopDetector(repeat_threshold=1)

        # Trigger 10 warnings
        for _ in range(10):
            detector.detect_tool_loop("same_tool", {"arg": 1})

        assert detector.total_warnings == 10

    def test_tool_warnings_tracks_per_tool(self):
        """tool_warnings tracks per-tool warning counts."""
        detector = LoopDetector(repeat_threshold=1)

        # Trigger warnings for different tools
        for _ in range(5):
            detector.detect_tool_loop("tool_a", {"arg": 1})
        for _ in range(3):
            detector.detect_tool_loop("tool_b", {"arg": 2})

        assert detector.tool_warnings.get("tool_a", 0) == 5
        assert detector.tool_warnings.get("tool_b", 0) == 3

    def test_reset_clears_cumulative_state(self):
        """reset() clears all escalation state."""
        detector = LoopDetector(repeat_threshold=1)

        for _ in range(5):
            detector.detect_tool_loop("tool", {})

        assert detector.total_warnings == 5
        detector.reset()
        assert detector.total_warnings == 0
        assert detector.tool_warnings == {}
        assert detector.escalation_level == 0


class TestEscalationLevels:
    """Test escalation level computation."""

    def test_level_0_below_threshold(self):
        """No escalation below warn_threshold."""
        detector = LoopDetector(
            repeat_threshold=1,
            warn_threshold=3,
        )
        # Trigger 2 warnings (below threshold)
        for _ in range(2):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 0

    def test_level_1_at_warn_threshold(self):
        """Level 1 at warn_threshold."""
        detector = LoopDetector(
            repeat_threshold=1,
            warn_threshold=3,
            inject_threshold=7,
        )
        for _ in range(3):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 1

    def test_level_2_at_inject_threshold(self):
        """Level 2 at inject_threshold."""
        detector = LoopDetector(
            repeat_threshold=1,
            warn_threshold=3,
            inject_threshold=7,
            force_think_threshold=11,
        )
        for _ in range(7):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 2

    def test_level_3_at_force_think_threshold(self):
        """Level 3 at force_think_threshold."""
        detector = LoopDetector(
            repeat_threshold=1,
            warn_threshold=3,
            inject_threshold=7,
            force_think_threshold=11,
            end_turn_threshold=15,
        )
        for _ in range(11):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 3

    def test_level_4_at_end_turn_threshold(self):
        """Level 4 at end_turn_threshold."""
        detector = LoopDetector(
            repeat_threshold=1,
            warn_threshold=3,
            inject_threshold=7,
            force_think_threshold=11,
            end_turn_threshold=15,
        )
        for _ in range(15):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 4


class TestEscalationInfo:
    """Test get_escalation_info() method."""

    def test_initial_state(self):
        """Initial state has no escalation."""
        detector = LoopDetector()
        info = detector.get_escalation_info()

        assert info["total_warnings"] == 0
        assert info["escalation_level"] == 0
        assert info["needs_injection"] is False
        assert info["needs_force_think"] is False

    def test_needs_injection_at_level_2(self):
        """needs_injection is True at level 2+."""
        detector = LoopDetector(
            repeat_threshold=1,
            inject_threshold=3,
        )
        for _ in range(3):
            detector.detect_tool_loop("tool", {})

        info = detector.get_escalation_info()
        assert info["needs_injection"] is True

    def test_needs_force_think_at_level_3(self):
        """needs_force_think is True at level 3+."""
        detector = LoopDetector(
            repeat_threshold=1,
            force_think_threshold=5,
        )
        for _ in range(5):
            detector.detect_tool_loop("tool", {})

        info = detector.get_escalation_info()
        assert info["needs_force_think"] is True


class TestWarningMessages:
    """Test escalating warning message content."""

    def test_level_1_message_format(self):
        """Level 1 message includes cumulative count."""
        detector = LoopDetector(
            repeat_threshold=1,
            warn_threshold=1,
            inject_threshold=100,  # High to stay at level 1
        )
        warning = detector.detect_tool_loop("test_tool", {})

        assert warning is not None
        assert "test_tool" in warning
        assert "#1" in warning  # Cumulative count

    def test_level_2_message_mentions_think(self):
        """Level 2 message suggests think tool."""
        detector = LoopDetector(
            repeat_threshold=1,
            warn_threshold=1,
            inject_threshold=2,
            force_think_threshold=100,
        )
        # Trigger level 1 warning
        detector.detect_tool_loop("tool", {})
        # Trigger level 2 warning
        warning = detector.detect_tool_loop("tool", {})

        assert warning is not None
        assert "think" in warning.lower()

    def test_level_3_message_is_critical(self):
        """Level 3 message is critical and directive."""
        detector = LoopDetector(
            repeat_threshold=1,
            warn_threshold=1,
            inject_threshold=2,
            force_think_threshold=3,
            end_turn_threshold=100,
        )
        detector.detect_tool_loop("tool", {})
        detector.detect_tool_loop("tool", {})
        warning = detector.detect_tool_loop("tool", {})

        assert warning is not None
        assert "MUST" in warning or "CRITICAL" in warning


class TestContextCompliance:
    """Test that escalation injection maintains OpenAI compliance."""

    def test_assistant_then_user_after_tool_results(self):
        """assistant(text) -> user(injection) is valid after tool results."""
        ctx = TauContext([
            {"role": "system", "content": "test"},
            {"role": "user", "content": "do something"},
            {"role": "assistant", "content": "", "tool_calls": [
                {"id": "c1", "function": {"name": "tool", "arguments": "{}"}}
            ]},
            {"role": "tool", "tool_call_id": "c1", "name": "c1", "content": "result"},
        ])

        # Simulate escalation injection
        ctx.append_assistant("I need to reconsider.", None)
        ctx.append_user("You are looping. Use think.")

        errors = ctx.validate()
        assert errors == [], f"Context validation failed: {errors}"

    def test_forced_end_turn_sequence(self):
        """force_end_turn produces valid context."""
        ctx = TauContext([
            {"role": "system", "content": "test"},
            {"role": "user", "content": "do something"},
            {"role": "assistant", "content": "", "tool_calls": [
                {"id": "c1", "function": {"name": "tool", "arguments": "{}"}}
            ]},
            {"role": "tool", "tool_call_id": "c1", "name": "c1", "content": "result"},
        ])

        # Simulate forced end of turn
        ctx.append_assistant("Loop detection forced termination.", None)

        errors = ctx.validate()
        assert errors == [], f"Context validation failed: {errors}"


class TestThinkFilter:
    """Test think-forcing via ToolFilter."""

    def test_think_only_filter(self):
        """ToolFilter allowlist={'think'} blocks other tools."""
        tf = ToolFilter(allowlist={"think"})

        assert tf.should_include("think") is True
        assert tf.should_include("bash") is False
        assert tf.should_include("file_read") is False

    def test_denied_message_includes_think(self):
        """Denial message mentions think tool."""
        tf = ToolFilter(
            allowlist={"think"},
            denied_message="Only 'think' is available. {tool_name} is blocked. Use: {available_tools}.",
        )
        msg = tf.format_denied("bash", ["think"])

        assert "think" in msg
        assert "bash" in msg


class TestSyntheticLoopSimulation:
    """Simulate a looping agent and verify escalation."""

    def test_loop_detection_progression(self):
        """Simulate loop calls and verify escalation progression."""
        detector = LoopDetector(
            repeat_threshold=1,
            warn_threshold=1,
            inject_threshold=3,
            force_think_threshold=5,
            end_turn_threshold=8,
        )

        escalation_history = []
        for i in range(10):
            detector.detect_tool_loop("same_tool", {"arg": 1})
            info = detector.get_escalation_info()
            escalation_history.append(info["escalation_level"])

        # Verify escalation progression
        assert escalation_history[0] == 1  # Level 1 at warning 1
        assert escalation_history[2] == 2  # Level 2 at warning 3
        assert escalation_history[4] == 3  # Level 3 at warning 5
        assert escalation_history[7] == 4  # Level 4 at warning 8

    def test_recovery_after_reset(self):
        """After reset, escalation starts fresh."""
        detector = LoopDetector(repeat_threshold=1, warn_threshold=2)

        # Trigger escalation
        for _ in range(5):
            detector.detect_tool_loop("tool", {})
        assert detector.escalation_level >= 1

        # Reset
        detector.reset()
        assert detector.escalation_level == 0

        # Start fresh
        detector.detect_tool_loop("tool", {})
        assert detector.total_warnings == 1
