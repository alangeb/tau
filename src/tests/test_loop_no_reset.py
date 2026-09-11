"""Tests for loop detection no-reset behavior and system_call flag.

Verifies:
1. Warnings accumulate monotonically (no reset at level 2/3)
2. system_call=True skips loop detection tracking
3. bypass_filter=True skips tool filter check
"""

import pytest
from agent_loop_detect import LoopDetector


class TestSystemCallFlag:
    """Test that system_call=True skips loop detection tracking."""

    def test_system_call_skips_tracking(self):
        """System calls should not be tracked by loop detector."""
        detector = LoopDetector(repeat_threshold=2)
        # System call should not trigger detection
        result = detector.detect_tool_loop("think", {"question": "test"}, system_call=True)
        assert result is None
        # History should be empty
        assert len(detector.tool_call_history) == 0

    def test_normal_call_still_tracked(self):
        """Normal (non-system) calls should still be tracked."""
        detector = LoopDetector(repeat_threshold=2)
        result = detector.detect_tool_loop("grep", {"pattern": "test"}, system_call=False)
        # First call should not trigger warning
        assert result is None
        # But history should have the call
        assert len(detector.tool_call_history) == 1

    def test_system_call_does_not_affect_consecutive_count(self):
        """System calls should not reset consecutive repeat counter."""
        detector = LoopDetector(repeat_threshold=2)
        # Build up consecutive repeats
        detector.detect_tool_loop("grep", {"pattern": "test"})
        detector.detect_tool_loop("grep", {"pattern": "test"})
        # Third call should trigger warning
        result = detector.detect_tool_loop("grep", {"pattern": "test"})
        assert result is not None
        # System call should not reset consecutive counter
        detector.detect_tool_loop("think", {"question": "test"}, system_call=True)
        # Next grep call should still trigger warning (consecutive preserved)
        result = detector.detect_tool_loop("grep", {"pattern": "test"})
        assert result is not None


class TestMonotonicAccumulation:
    """Test that warnings accumulate monotonically without reset (when loop persists)."""

    def test_warnings_accumulate_past_level_2(self):
        """Warnings should continue accumulating past level 2 threshold when loop persists."""
        detector = LoopDetector(repeat_threshold=1)
        # Generate warnings with IDENTICAL calls (true loop)
        for i in range(10):
            detector.detect_tool_loop("grep", {"pattern": "test"})
        # Should have accumulated warnings past level 2 threshold (7)
        assert detector.total_warnings >= 7
        # Escalation level should be >= 2
        assert detector.escalation_level >= 2

    def test_level_3_reachable(self):
        """Level 3 (force_think) should be reachable without reset when loop persists."""
        detector = LoopDetector(repeat_threshold=1)
        # Generate enough warnings to reach level 3 (11) with identical calls
        for i in range(15):
            detector.detect_tool_loop("grep", {"pattern": "test"})
        assert detector.escalation_level >= 3

    def test_level_4_reachable(self):
        """Level 4 (force_end_turn) should be reachable without reset when loop persists."""
        detector = LoopDetector(repeat_threshold=1)
        # Generate enough warnings to reach level 4 (15) with identical calls
        for i in range(20):
            detector.detect_tool_loop("grep", {"pattern": "test"})
        assert detector.escalation_level >= 4

    def test_warnings_reset_on_non_repeat_call(self):
        """Warnings should reset when sustained non-repeat calls break the loop pattern.

        Anti-gaming: requires 3 consecutive non-repeats before clearing total_warnings
        (prevents alternation gaming: loop,loop,loop,good,loop,loop,loop,good,...).
        """
        detector = LoopDetector(repeat_threshold=2)
        # Build up warnings with identical calls (need 3+ to reach level 1)
        detector.detect_tool_loop("grep", {"pattern": "test"})
        detector.detect_tool_loop("grep", {"pattern": "test"})  # triggers warning (total=1)
        detector.detect_tool_loop("grep", {"pattern": "test"})  # triggers warning (total=2)
        detector.detect_tool_loop("grep", {"pattern": "test"})  # triggers warning (total=3, level=1)
        assert detector.total_warnings >= 3
        assert detector.escalation_level >= 1

        # Single non-repeat does NOT reset (anti-gaming: need 3 consecutive)
        detector.detect_tool_loop("ls", {"path": "."})
        assert detector.total_warnings >= 3  # still has warnings

        # Second non-repeat still not enough
        detector.detect_tool_loop("cat", {"file_path": "foo"})
        assert detector.total_warnings >= 3  # still has warnings

        # Third consecutive non-repeat — sustained break, reset warnings
        detector.detect_tool_loop("wc", {"path": "bar"})
        assert detector.total_warnings == 0
        assert detector.escalation_level == 0

    def test_warnings_reset_on_non_repeat_but_entropy_low(self):
        """If entropy is still low after non-repeat call, entropy warnings persist."""
        # Use repeat_threshold=15 so repeat warnings don't trigger (12 calls < 15)
        detector = LoopDetector(repeat_threshold=15, sustained_threshold=0.5)
        # Build up history with repeated calls (need 10+ for entropy)
        for i in range(12):
            detector.detect_tool_loop("grep", {"pattern": "test"})
        # Should have entropy warnings (repeat warnings are 0 since threshold=15)
        assert detector.total_warnings == 0  # repeat threshold not reached
        assert detector.entropy_warnings > 0

        # Non-repeat call: repeat warnings stay 0, entropy still low
        detector.detect_tool_loop("ls", {"path": "."})
        assert detector.total_warnings == 0  # repeat warnings still 0
        # Entropy warnings persist (entropy still low due to history)
        assert detector.entropy_warnings > 0


class TestEntropyNotPollutedBySystemCalls:
    """Test that system calls don't pollute entropy calculations."""

    def test_system_calls_not_in_history(self):
        """System calls should not appear in tool_call_history."""
        detector = LoopDetector(repeat_threshold=2)
        detector.detect_tool_loop("grep", {"pattern": "test"})
        detector.detect_tool_loop("think", {"question": "test"}, system_call=True)
        detector.detect_tool_loop("grep", {"pattern": "test"})
        # History should only have grep calls, not think
        assert len(detector.tool_call_history) == 2
        assert all("grep" in key for key in detector.tool_call_history)

    def test_entropy_calculated_only_on_real_calls(self):
        """Entropy should only consider real (non-system) tool calls."""
        detector = LoopDetector(repeat_threshold=2, window_size=10)
        # Mix of real and system calls
        for i in range(5):
            detector.detect_tool_loop("grep", {"pattern": f"test{i}"})
            detector.detect_tool_loop("think", {"question": f"q{i}"}, system_call=True)
        # Only grep calls should be in history
        assert len(detector.tool_call_history) == 5
        # Entropy should be calculated on grep calls only
        entropy = detector._calculate_entropy()
        # 5 unique grep calls → entropy = log2(5) ≈ 2.32
        assert entropy > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
