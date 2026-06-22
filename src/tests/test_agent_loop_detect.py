"""Tests for agent_loop_detect module."""

from agent_loop_detect import LoopDetector


class TestLoopDetector:
    """Test LoopDetector class."""

    def test_no_loop_on_diverse_calls(self):
        """Test no loop detected with diverse tool calls."""
        detector = LoopDetector()

        # Different tool calls
        detector.detect_tool_loop("tool_a", {"arg": 1})
        detector.detect_tool_loop("tool_b", {"arg": 2})
        detector.detect_tool_loop("tool_c", {"arg": 3})

        # Should not trigger loop
        assert detector.consecutive_repeats == 1

    def test_repeat_loop_detection(self):
        """Test repeat loop detection."""
        detector = LoopDetector(repeat_threshold=3)

        # Same tool call 3 times
        warning1 = detector.detect_tool_loop("same_tool", {"arg": 1})
        warning2 = detector.detect_tool_loop("same_tool", {"arg": 1})
        warning3 = detector.detect_tool_loop("same_tool", {"arg": 1})

        # Third call should trigger warning
        assert warning1 is None
        assert warning2 is None
        assert warning3 is not None

    def test_entropy_calculation(self):
        """Test entropy calculation."""
        detector = LoopDetector(window_size=10)

        # Add diverse calls
        for i in range(10):
            detector.detect_tool_loop(f"tool_{i}", {"arg": i})

        stats = detector.get_stats()
        assert stats["entropy"] > 1.0  # Diverse = high entropy

    def test_reset(self):
        """Test reset functionality."""
        detector = LoopDetector()

        detector.detect_tool_loop("tool", {})
        detector.reset()

        assert detector.consecutive_repeats == 0
        assert len(detector.tool_call_history) == 0

    def test_entropy_low_with_repeated_calls(self):
        """Test entropy drops with repeated calls."""
        detector = LoopDetector(window_size=10)

        # Same call repeatedly
        for _ in range(15):
            detector.detect_tool_loop("same_tool", {"arg": 1})

        stats = detector.get_stats()
        # Single unique call = entropy of 0
        assert stats["entropy"] == 0.0

    def test_ab_ab_pattern(self):
        """Test A-B-A-B pattern detection."""
        detector = LoopDetector(window_size=10)

        # A-B alternating pattern
        for i in range(10):
            if i % 2 == 0:
                detector.detect_tool_loop("tool_a", {"arg": i})
            else:
                detector.detect_tool_loop("tool_b", {"arg": i})

        stats = detector.get_stats()
        # Two unique patterns, but with different args each time
        # Should still have some entropy
        assert stats["entropy"] > 0

    def test_tool_call_key_generation(self):
        """Test tool call key generation."""
        detector = LoopDetector()

        # Same tool, same args = same key
        key1 = detector._tool_call_key("test_tool", {"a": 1, "b": 2})
        key2 = detector._tool_call_key("test_tool", {"b": 2, "a": 1})

        # Keys should be identical (sorted keys)
        assert key1 == key2

    def test_get_stats(self):
        """Test stats retrieval."""
        detector = LoopDetector(window_size=30)

        for i in range(5):
            detector.detect_tool_loop(f"tool_{i}", {"arg": i})

        stats = detector.get_stats()

        assert "entropy" in stats
        assert "history_size" in stats
        assert "consecutive_repeats" in stats
        assert stats["history_size"] == 5
