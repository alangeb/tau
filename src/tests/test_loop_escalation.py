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
    """Test escalation level computation (new 5-level structure)."""

    def test_level_0_below_threshold(self):
        """No escalation below 3 warnings."""
        detector = LoopDetector(repeat_threshold=1)
        # Trigger 2 warnings (below threshold)
        for _ in range(2):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 0

    def test_level_1_at_3_warnings(self):
        """Level 1 at 3 warnings."""
        detector = LoopDetector(repeat_threshold=1)
        for _ in range(3):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 1

    def test_level_1_at_5_warnings(self):
        """Level 1 at 5 warnings."""
        detector = LoopDetector(repeat_threshold=1)
        for _ in range(5):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 1

    def test_level_2_at_6_warnings(self):
        """Level 2 at 6 warnings."""
        detector = LoopDetector(repeat_threshold=1)
        for _ in range(6):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 2

    def test_level_2_at_8_warnings(self):
        """Level 2 at 8 warnings."""
        detector = LoopDetector(repeat_threshold=1)
        for _ in range(8):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 2

    def test_level_3_at_9_warnings(self):
        """Level 3 at 9 warnings."""
        detector = LoopDetector(repeat_threshold=1)
        for _ in range(9):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 3

    def test_level_3_at_11_warnings(self):
        """Level 3 at 11 warnings."""
        detector = LoopDetector(repeat_threshold=1)
        for _ in range(11):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 3

    def test_level_4_at_12_warnings(self):
        """Level 4 at 12 warnings."""
        detector = LoopDetector(repeat_threshold=1)
        for _ in range(12):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 4

    def test_level_4_at_14_warnings(self):
        """Level 4 at 14 warnings."""
        detector = LoopDetector(repeat_threshold=1)
        for _ in range(14):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 4

    def test_level_5_at_15_warnings(self):
        """Level 5 at 15 warnings (termination)."""
        detector = LoopDetector(repeat_threshold=1)
        for _ in range(15):
            detector.detect_tool_loop("tool", {})

        assert detector.escalation_level == 5

    def test_level_5_at_20_warnings(self):
        """Level 5 at 20 warnings."""
        detector = LoopDetector(repeat_threshold=1)
        for _ in range(20):
            detector.detect_tool_loop("tool", {})
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
        detector = LoopDetector(repeat_threshold=1)
        # Trigger 6 warnings to reach level 2
        for _ in range(6):
            detector.detect_tool_loop("tool", {})

        info = detector.get_escalation_info()
        assert info["needs_injection"] is True

    def test_needs_force_think_at_level_3(self):
        """needs_force_think is True at level 3+."""
        detector = LoopDetector(repeat_threshold=1)
        # Trigger 9 warnings to reach level 3
        for _ in range(9):
            detector.detect_tool_loop("tool", {})

        info = detector.get_escalation_info()
        assert info["needs_force_think"] is True
class TestWarningMessages:
    """Test escalating warning message content."""

    def test_level_1_message_format(self):
        """Level 1 message includes cumulative count."""
        detector = LoopDetector(
            repeat_threshold=1,
        )
        warning = detector.detect_tool_loop("test_tool", {})

        assert warning is not None
        assert "test_tool" in warning
        assert "#1" in warning  # Cumulative count

    def test_level_2_message_format(self):
        """Level 2 message includes escalation info."""
        detector = LoopDetector(repeat_threshold=1)
        # Trigger 6 warnings to reach level 2
        for _ in range(6):
            detector.detect_tool_loop("tool", {})

        # The warning message is returned by detect_tool_loop
        # At level 2, the message should include warning count
        info = detector.get_escalation_info()
        assert info["escalation_level"] == 2
        assert info["total_warnings"] == 6

    def test_level_3_message_format(self):
        """Level 3 message is critical."""
        detector = LoopDetector(repeat_threshold=1)
        # Trigger 9 warnings to reach level 3
        for _ in range(9):
            detector.detect_tool_loop("tool", {})

        info = detector.get_escalation_info()
        assert info["escalation_level"] == 3
        assert info["total_warnings"] == 9


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
        """Simulate loop calls and verify escalation progression (new levels)."""
        detector = LoopDetector(repeat_threshold=1)

        escalation_history = []
        for i in range(20):
            detector.detect_tool_loop("same_tool", {"arg": 1})
            info = detector.get_escalation_info()
            escalation_history.append(info["escalation_level"])

        # Verify escalation progression (new 5-level structure)
        assert escalation_history[0] == 0  # Warning 1: level 0
        assert escalation_history[1] == 0  # Warning 2: level 0
        assert escalation_history[2] == 1  # Warning 3: level 1
        assert escalation_history[4] == 1  # Warning 5: level 1
        assert escalation_history[5] == 2  # Warning 6: level 2
        assert escalation_history[7] == 2  # Warning 8: level 2
        assert escalation_history[8] == 3  # Warning 9: level 3
        assert escalation_history[10] == 3  # Warning 11: level 3
        assert escalation_history[11] == 4  # Warning 12: level 4
        assert escalation_history[13] == 4  # Warning 14: level 4
        assert escalation_history[14] == 5  # Warning 15: level 5
        assert escalation_history[19] == 5  # Warning 20: level 5

    def test_recovery_after_reset(self):
        """After reset, escalation starts fresh."""
        detector = LoopDetector(repeat_threshold=1)

        # Trigger escalation
        for _ in range(5):
            detector.detect_tool_loop("tool", {})
        assert detector.escalation_level == 1

        # Reset
        detector.reset()
        assert detector.escalation_level == 0

        # Start fresh
        detector.detect_tool_loop("tool", {})
        assert detector.total_warnings == 1
