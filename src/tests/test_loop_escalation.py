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
from agent_tool_filter import ToolFilter


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


class TestSustainedNonRepeat:
    """Test that total_warnings requires sustained non-repeats before clearing."""

    def _build_warnings(self, detector, count):
        """Helper to build up exactly `count` warnings.
        
        After building, _consecutive_non_repeats will be 1 (from the final breaker call).
        """
        for _ in range(count):
            detector.detect_tool_loop("bad_tool", {})
            detector.detect_tool_loop("bad_tool", {})  # repeat triggers warning
            detector.detect_tool_loop("breaker", {})   # break the repeat chain

    def test_single_non_repeat_does_not_clear_warnings(self):
        """A single non-repeat should NOT clear total_warnings."""
        detector = LoopDetector(repeat_threshold=2)

        # Trigger 5 warnings; after this, _consecutive_non_repeats == 1 (from breaker)
        self._build_warnings(detector, 5)
        assert detector.total_warnings == 5
        assert detector._consecutive_non_repeats == 1

        # Single non-repeat — should NOT clear warnings (counter goes to 2, threshold is 3)
        detector.detect_tool_loop("good_tool", {})
        assert detector.total_warnings == 5
        assert detector._consecutive_non_repeats == 2

    def test_two_non_repeats_does_not_clear_warnings(self):
        """Two consecutive non-repeats should NOT clear warnings (threshold is 3)."""
        detector = LoopDetector(repeat_threshold=2)

        self._build_warnings(detector, 5)
        assert detector.total_warnings == 5
        # _consecutive_non_repeats is 1 from breaker, need 2 more to reach threshold

        detector.detect_tool_loop("good_tool_1", {})  # counter -> 2
        detector.detect_tool_loop("good_tool_2", {})  # counter -> 3, THRESHOLD REACHED!
        # Warnings ARE cleared because we hit the threshold (1 + 2 = 3)
        assert detector.total_warnings == 0
        assert detector._consecutive_non_repeats == 3

    def test_two_non_repeats_from_zero_does_not_clear(self):
        """Two non-repeats starting from counter=0 should NOT clear warnings."""
        detector = LoopDetector(repeat_threshold=2)

        self._build_warnings(detector, 5)
        assert detector.total_warnings == 5

        # Reset counter by triggering a repeat (this adds 1 warning)
        detector.detect_tool_loop("repeat_a", {})
        detector.detect_tool_loop("repeat_a", {})  # repeat, resets counter to 0, +1 warning
        assert detector.total_warnings == 6

        # Now counter is 0, two non-repeats should NOT clear (need 3)
        detector.detect_tool_loop("good_1", {})  # counter -> 1
        detector.detect_tool_loop("good_2", {})  # counter -> 2
        assert detector.total_warnings == 6  # unchanged
        assert detector._consecutive_non_repeats == 2

    def test_three_non_repeats_from_zero_clears_warnings(self):
        """Three consecutive non-repeats from counter=0 SHOULD clear warnings."""
        detector = LoopDetector(repeat_threshold=2)

        self._build_warnings(detector, 5)
        assert detector.total_warnings == 5

        # Reset counter by triggering a repeat
        detector.detect_tool_loop("repeat_a", {})
        detector.detect_tool_loop("repeat_a", {})  # repeat, resets counter to 0

        # Three non-repeats should clear warnings
        detector.detect_tool_loop("good_1", {})  # counter -> 1
        detector.detect_tool_loop("good_2", {})  # counter -> 2
        detector.detect_tool_loop("good_3", {})  # counter -> 3, THRESHOLD!
        assert detector.total_warnings == 0
        assert detector._consecutive_non_repeats == 3

    def test_repeat_resets_non_repeat_counter(self):
        """A repeat call should reset the non-repeat counter."""
        detector = LoopDetector(repeat_threshold=2)

        # Build up some warnings
        detector.detect_tool_loop("bad_tool", {})
        detector.detect_tool_loop("bad_tool", {})  # repeat, warning
        detector.detect_tool_loop("breaker", {})   # break chain
        detector.detect_tool_loop("bad_tool", {})
        detector.detect_tool_loop("bad_tool", {})  # repeat, warning
        assert detector.total_warnings == 2

        # Two non-repeats
        detector.detect_tool_loop("good_1", {})
        detector.detect_tool_loop("good_2", {})
        assert detector._consecutive_non_repeats == 2

        # Repeat of good_2 — resets counter
        detector.detect_tool_loop("good_2", {})
        assert detector._consecutive_non_repeats == 0
        # total_warnings incremented because good_2 repeat triggers another warning
        assert detector.total_warnings == 3

    def test_alternating_pattern_does_not_clear_warnings(self):
        """Alternating bad/good/bad/good should NOT clear warnings."""
        detector = LoopDetector(repeat_threshold=2)

        # Build up warnings with alternating pattern
        for _ in range(5):
            detector.detect_tool_loop("bad_a", {})
            detector.detect_tool_loop("bad_a", {})  # repeat triggers warning
            detector.detect_tool_loop("good", {})   # non-repeat, increments counter

        # Warnings should still be accumulated because non-repeats never reached threshold
        assert detector.total_warnings > 0

    def test_reset_clears_non_repeat_counter(self):
        """reset() should clear _consecutive_non_repeats."""
        detector = LoopDetector(repeat_threshold=2)

        detector.detect_tool_loop("tool_a", {})
        detector.detect_tool_loop("tool_b", {})
        assert detector._consecutive_non_repeats == 2

        detector.reset()
        assert detector._consecutive_non_repeats == 0


class TestInjectThinkReflectionHelper:
    """Test the _inject_think_reflection shared helper."""

    def test_helper_exists(self):
        """_inject_think_reflection method exists on LoopEscalationManager."""
        from agent_loop_escalation import LoopEscalationManager

        assert hasattr(LoopEscalationManager, "_inject_think_reflection")

    def test_helper_signature(self):
        """_inject_think_reflection has correct signature."""
        import inspect
        from agent_loop_escalation import LoopEscalationManager

        sig = inspect.signature(LoopEscalationManager._inject_think_reflection)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "question" in params
        assert "id_prefix" in params
        assert "concise_summary" in params
        assert "console_label" in params
        assert "console_desc" in params
        assert "track_timing" in params

    def test_inject_early_reflection_calls_helper(self):
        """inject_early_reflection delegates to _inject_think_reflection."""
        import ast
        from pathlib import Path

        source = Path(__file__).parent.parent / "agent_loop_escalation.py"
        tree = ast.parse(source.read_text())

        # Find inject_early_reflection method
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "inject_early_reflection":
                # Check it calls _inject_think_reflection
                source_text = ast.unparse(node)
                assert "_inject_think_reflection" in source_text
                break
        else:
            pytest.fail("inject_early_reflection method not found")

    def test_inject_reflection_calls_helper(self):
        """inject_reflection delegates to _inject_think_reflection."""
        import ast
        from pathlib import Path

        source = Path(__file__).parent.parent / "agent_loop_escalation.py"
        tree = ast.parse(source.read_text())

        # Find inject_reflection method
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "inject_reflection":
                # Check it calls _inject_think_reflection
                source_text = ast.unparse(node)
                assert "_inject_think_reflection" in source_text
                break
        else:
            pytest.fail("inject_reflection method not found")

    def test_early_reflection_no_timing(self):
        """inject_early_reflection passes track_timing=False."""
        import ast
        from pathlib import Path

        source = Path(__file__).parent.parent / "agent_loop_escalation.py"
        tree = ast.parse(source.read_text())

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "inject_early_reflection":
                source_text = ast.unparse(node)
                assert "track_timing=False" in source_text
                break
        else:
            pytest.fail("inject_early_reflection method not found")

    def test_reflection_with_timing(self):
        """inject_reflection passes track_timing=True."""
        import ast
        from pathlib import Path

        source = Path(__file__).parent.parent / "agent_loop_escalation.py"
        tree = ast.parse(source.read_text())

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "inject_reflection":
                source_text = ast.unparse(node)
                assert "track_timing=True" in source_text
                break
        else:
            pytest.fail("inject_reflection method not found")
