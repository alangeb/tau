"""Tests for pure validation functions in agent_context_validation.

Tests the extracted validation functions directly, without going through
TauContext. This ensures the pure functions work correctly on plain message
lists.
"""

from agent_context_validation import (
    validate_context,
    get_pending_tool_ids,
    validate_tool_resolution,
    _validate_assistant_tool_calls,
    _validate_content,
    _validate_tool_message,
)


class TestValidateAssistantToolCalls:
    """Test _validate_assistant_tool_calls pure function."""

    def test_valid_tool_calls(self):
        """Valid tool_calls array passes validation."""
        msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "t1", "function": {"name": "test", "arguments": "{}"}},
            ],
        }
        errors = _validate_assistant_tool_calls(msg, 0)
        assert errors == []

    def test_missing_id(self):
        """Missing id field produces single error (no duplicate)."""
        msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "test", "arguments": "{}"}},
            ],
        }
        errors = _validate_assistant_tool_calls(msg, 0)
        # Should have exactly one error about missing id, not two
        id_errors = [e for e in errors if "missing 'id'" in e]
        assert len(id_errors) == 1

    def test_duplicate_ids(self):
        """Duplicate tool_call_ids are detected."""
        msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "t1", "function": {"name": "test", "arguments": "{}"}},
                {"id": "t1", "function": {"name": "test", "arguments": "{}"}},
            ],
        }
        errors = _validate_assistant_tool_calls(msg, 0)
        assert any("duplicate" in e for e in errors)

    def test_invalid_arguments(self):
        """Invalid JSON in arguments is detected."""
        msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "t1", "function": {"name": "test", "arguments": "not-json"}},
            ],
        }
        errors = _validate_assistant_tool_calls(msg, 0)
        assert any("valid JSON" in e for e in errors)


class TestValidateContent:
    """Test _validate_content pure function."""

    def test_valid_content(self):
        """Valid content passes validation."""
        msg = {"role": "user", "content": "hello"}
        errors = _validate_content(msg, 0)
        assert errors == []

    def test_none_content(self):
        """None content fails validation."""
        msg = {"role": "user", "content": None}
        errors = _validate_content(msg, 0)
        assert len(errors) > 0

    def test_empty_content(self):
        """Empty content fails validation."""
        msg = {"role": "user", "content": ""}
        errors = _validate_content(msg, 0)
        assert len(errors) > 0

    def test_tool_role_skipped(self):
        """Tool messages skip content validation."""
        msg = {"role": "tool", "content": None}
        errors = _validate_content(msg, 0)
        assert errors == []


class TestValidateToolMessage:
    """Test _validate_tool_message pure function."""

    def test_valid_tool_message(self):
        """Valid tool message passes validation."""
        msg = {
            "role": "tool",
            "tool_call_id": "t1",
            "name": "test",
            "content": "result",
        }
        errors = _validate_tool_message(msg, 0)
        assert errors == []

    def test_missing_tool_call_id(self):
        """Missing tool_call_id is detected."""
        msg = {"role": "tool", "name": "test", "content": "result"}
        errors = _validate_tool_message(msg, 0)
        assert any("tool_call_id" in e for e in errors)


class TestValidateContext:
    """Test validate_context pure function."""

    def test_empty_context(self):
        """Empty context is valid."""
        errors = validate_context([])
        assert errors == []

    def test_valid_context(self):
        """Valid context passes validation."""
        messages = [
            {"role": "system", "content": "test"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        errors = validate_context(messages)
        assert errors == []

    def test_missing_system(self):
        """Missing system message is detected."""
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        errors = validate_context(messages)
        assert any("system" in e.lower() for e in errors)

    def test_consecutive_roles(self):
        """Consecutive same-role messages are detected."""
        messages = [
            {"role": "system", "content": "test"},
            {"role": "user", "content": "hello"},
            {"role": "user", "content": "world"},
        ]
        errors = validate_context(messages)
        assert any("consecutive" in e.lower() for e in errors)

    def test_non_dict_entry(self):
        """Non-dict entries are detected."""
        messages = [
            {"role": "system", "content": "test"},
            "not a dict",
        ]
        errors = validate_context(messages)
        assert any("not a dictionary" in e for e in errors)


class TestGetPendingToolIds:
    """Test get_pending_tool_ids pure function."""

    def test_no_pending(self):
        """No pending tool calls."""
        messages = [
            {"role": "system", "content": "test"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        pending = get_pending_tool_ids(messages)
        assert pending == set()

    def test_pending_tool_calls(self):
        """Pending tool calls are detected."""
        messages = [
            {"role": "system", "content": "test"},
            {"role": "user", "content": "hello"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": "t1", "function": {"name": "test", "arguments": "{}"}},
                ],
            },
        ]
        pending = get_pending_tool_ids(messages)
        assert pending == {"t1"}

    def test_resolved_tool_calls(self):
        """Resolved tool calls are not pending."""
        messages = [
            {"role": "system", "content": "test"},
            {"role": "user", "content": "hello"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": "t1", "function": {"name": "test", "arguments": "{}"}},
                ],
            },
            {"role": "tool", "tool_call_id": "t1", "name": "test", "content": "result"},
        ]
        pending = get_pending_tool_ids(messages)
        assert pending == set()


class TestValidateToolResolution:
    """Test validate_tool_resolution pure function."""

    def test_resolved(self):
        """Resolved tool calls pass validation."""
        messages = [
            {"role": "system", "content": "test"},
            {"role": "user", "content": "hello"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": "t1", "function": {"name": "test", "arguments": "{}"}},
                ],
            },
            {"role": "tool", "tool_call_id": "t1", "name": "test", "content": "result"},
        ]
        errors = validate_tool_resolution(messages)
        assert errors == []

    def test_unresolved(self):
        """Unresolved tool calls fail validation."""
        messages = [
            {"role": "system", "content": "test"},
            {"role": "user", "content": "hello"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": "t1", "function": {"name": "test", "arguments": "{}"}},
                ],
            },
        ]
        errors = validate_tool_resolution(messages)
        assert len(errors) > 0


class TestValidateOnMutation:
    """Test validate_on_mutation with mid-batch suppression."""

    def test_mid_batch_suppresses_unresolved_tools(self):
        """Mid-batch context suppresses unresolved tool call warnings."""
        from agent_context_validation import validate_on_mutation

        messages = [
            {"role": "system", "content": "test"},
            {"role": "user", "content": "hello"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": "t1", "function": {"name": "test", "arguments": "{}"}},
                ],
            },
        ]
        # Should not crash — mid-batch suppression kicks in
        validate_on_mutation(messages)

    def test_mid_batch_suppresses_consecutive_roles(self):
        """Mid-batch context suppresses consecutive role warnings."""
        from agent_context_validation import validate_on_mutation

        messages = [
            {"role": "system", "content": "test"},
            {"role": "user", "content": "hello"},
            {"role": "tool", "tool_call_id": "t1", "name": "test", "content": "result"},
            {"role": "tool", "tool_call_id": "t2", "name": "test2", "content": "result"},
        ]
        # Should not crash — mid-batch suppression kicks in
        validate_on_mutation(messages)