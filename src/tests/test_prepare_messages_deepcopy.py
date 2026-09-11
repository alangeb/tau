"""Tests for _prepare_messages() deep copy behavior.

Verifies that _prepare_messages() does NOT mutate the original context's
tool_calls dicts when stripping non-API fields.
"""

import copy
from agent_llm_invoke import _prepare_messages
from agent_llm_models import _ALLOWED_TOOL_CALL_FIELDS


class TestPrepareMessagesDeepCopy:
    """Test that _prepare_messages does not mutate original context."""

    def test_tool_calls_not_mutated(self):
        """Original tool_calls should NOT be mutated when extra keys are stripped."""
        original_tc = {
            "id": "call_123",
            "type": "function",
            "function": {"name": "test_tool", "arguments": "{}"},
            "extra_key": "should_be_removed",
        }
        messages = [
            {"role": "assistant", "content": None, "tool_calls": [original_tc]}
        ]

        result = _prepare_messages(messages)

        # Result should have extra_key stripped
        assert "extra_key" not in result[0]["tool_calls"][0]

        # Original should NOT be mutated
        assert "extra_key" in original_tc, (
            "FAIL: Original tool_calls was mutated by _prepare_messages!"
        )

    def test_nested_function_dict_not_mutated(self):
        """Nested function dict should also be preserved."""
        original_tc = {
            "id": "call_456",
            "type": "function",
            "function": {
                "name": "file_read",
                "arguments": '{"file_path": "test.txt"}',
                "extra_nested": "should_be_removed",
            },
        }
        original_copy = copy.deepcopy(original_tc)
        messages = [
            {"role": "assistant", "content": None, "tool_calls": [original_tc]}
        ]

        result = _prepare_messages(messages)

        # Original should be completely unchanged
        assert original_tc == original_copy, (
            "FAIL: Original tool_calls was mutated (nested dict)!"
        )

    def test_multiple_tool_calls_all_preserved(self):
        """All tool_calls in a message should be preserved."""
        tc1 = {
            "id": "call_1",
            "type": "function",
            "function": {"name": "tool1", "arguments": "{}"},
            "extra": "remove1",
        }
        tc2 = {
            "id": "call_2",
            "type": "function",
            "function": {"name": "tool2", "arguments": "{}"},
            "extra": "remove2",
        }
        original_tc1 = copy.deepcopy(tc1)
        original_tc2 = copy.deepcopy(tc2)
        messages = [
            {"role": "assistant", "content": None, "tool_calls": [tc1, tc2]}
        ]

        result = _prepare_messages(messages)

        # Both originals should be unchanged
        assert tc1 == original_tc1
        assert tc2 == original_tc2

    def test_no_tool_calls_unchanged(self):
        """Messages without tool_calls should work normally."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        result = _prepare_messages(messages)
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    def test_empty_tool_calls_list(self):
        """Empty tool_calls list should not cause errors."""
        messages = [
            {"role": "assistant", "content": None, "tool_calls": []}
        ]
        result = _prepare_messages(messages)
        assert result[0]["tool_calls"] == []

    def test_allowed_fields_preserved_in_result(self):
        """Allowed fields should be present in the result."""
        original_tc = {
            "id": "call_789",
            "type": "function",
            "function": {"name": "test", "arguments": "{}"},
            "extra": "remove",
        }
        messages = [
            {"role": "assistant", "content": None, "tool_calls": [original_tc]}
        ]

        result = _prepare_messages(messages)
        tc_result = result[0]["tool_calls"][0]

        # Allowed fields should be present
        for field in _ALLOWED_TOOL_CALL_FIELDS:
            if field in original_tc:
                assert field in tc_result, f"Missing allowed field: {field}"

        # Extra fields should be stripped
        assert "extra" not in tc_result
