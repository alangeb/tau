"""End-to-end tests for batched tool calls.

Tests the complete flow of batched tool calls from LLM response to context validation.
Tests cover:
    - Single and multiple batched tool calls
    - Sequential batches
    - Pending tool detection
    - Invalid tool references
    - Consecutive message validation
    - System message positioning
    - Complex multi-batch scenarios
"""

from agent_context import TauContext


class TestBatchedToolCallsE2E:
    """End-to-end tests for batched tool call support."""

    def test_single_tool_call(self):
        """Single tool call (baseline behavior)."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Get time"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "t1",
                            "function": {"name": "get_time", "arguments": "{}"},
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t1",
                    "name": "t1",
                    "content": "12:00",
                },
                {"role": "assistant", "content": "It is 12:00"},
            ]
        )
        assert context.validate() == []
        assert not context.is_tool_pending()

    def test_two_batched_tools(self):
        """Two tools in one batch."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Get weather and temp"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "t1",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        },
                        {
                            "id": "t2",
                            "function": {"name": "get_temperature", "arguments": "{}"},
                        },
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t1",
                    "name": "t1",
                    "content": "sunny",
                },
                {"role": "tool", "tool_call_id": "t2", "name": "t2", "content": "25c"},
                {"role": "assistant", "content": "It's sunny and 25c"},
            ]
        )
        assert context.validate() == []
        assert not context.is_tool_pending()

    def test_three_batched_tools(self):
        """Three tools in one batch."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Get weather, temp, humidity"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "t1",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        },
                        {
                            "id": "t2",
                            "function": {"name": "get_temperature", "arguments": "{}"},
                        },
                        {
                            "id": "t3",
                            "function": {"name": "get_humidity", "arguments": "{}"},
                        },
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t1",
                    "name": "t1",
                    "content": "sunny",
                },
                {"role": "tool", "tool_call_id": "t2", "name": "t2", "content": "25c"},
                {"role": "tool", "tool_call_id": "t3", "name": "t3", "content": "60%"},
                {"role": "assistant", "content": "It's sunny, 25c, 60% humidity"},
            ]
        )
        assert context.validate() == []
        assert not context.is_tool_pending()

    def test_four_batched_tools(self):
        """Four tools in one batch (stress test)."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Get all info"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "t1",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        },
                        {
                            "id": "t2",
                            "function": {"name": "get_temperature", "arguments": "{}"},
                        },
                        {
                            "id": "t3",
                            "function": {"name": "get_humidity", "arguments": "{}"},
                        },
                        {
                            "id": "t4",
                            "function": {"name": "get_pressure", "arguments": "{}"},
                        },
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t1",
                    "name": "t1",
                    "content": "sunny",
                },
                {"role": "tool", "tool_call_id": "t2", "name": "t2", "content": "25c"},
                {"role": "tool", "tool_call_id": "t3", "name": "t3", "content": "60%"},
                {
                    "role": "tool",
                    "tool_call_id": "t4",
                    "name": "t4",
                    "content": "1013hPa",
                },
                {"role": "assistant", "content": "All weather info retrieved"},
            ]
        )
        assert context.validate() == []
        assert not context.is_tool_pending()

    def test_multiple_batches_sequential(self):
        """Multiple batches: batch1 → batch2."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Get Vienna weather"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "t1",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t1",
                    "name": "t1",
                    "content": "sunny",
                },
                {"role": "assistant", "content": "Vienna is sunny"},
                {"role": "user", "content": "Get Berlin temp"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "t2",
                            "function": {"name": "get_temperature", "arguments": "{}"},
                        }
                    ],
                },
                {"role": "tool", "tool_call_id": "t2", "name": "t2", "content": "20c"},
                {"role": "assistant", "content": "Berlin is 20c"},
            ]
        )
        assert context.validate() == []
        assert not context.is_tool_pending()

    def test_pending_tool_prevents_assistant(self):
        """Assistant blocked until all tools resolved."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Get weather and temp"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "t1",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        },
                        {
                            "id": "t2",
                            "function": {"name": "get_temperature", "arguments": "{}"},
                        },
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t1",
                    "name": "t1",
                    "content": "sunny",
                },
                # Missing t2!
                {"role": "assistant", "content": "It's sunny"},
            ]
        )
        errors = context.validate()
        assert len(errors) > 0
        assert any("pending tool calls" in e for e in errors)
        assert "t2" in str(errors)

    def test_invalid_tool_reference(self):
        """Tool references unknown tool_call_id."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Get weather"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "t1",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t99",
                    "name": "t99",
                    "content": "sunny",
                },  # Unknown!
            ]
        )
        errors = context.validate()
        assert len(errors) > 0
        assert any("non-existent tool_call_id" in e for e in errors)

    def test_consecutive_tool_messages_allowed(self):
        """Tool → tool → tool sequences are allowed."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "t1",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        },
                        {
                            "id": "t2",
                            "function": {"name": "get_temperature", "arguments": "{}"},
                        },
                        {
                            "id": "t3",
                            "function": {"name": "get_humidity", "arguments": "{}"},
                        },
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t1",
                    "name": "t1",
                    "content": "sunny",
                },
                {"role": "tool", "tool_call_id": "t2", "name": "t2", "content": "25c"},
                {"role": "tool", "tool_call_id": "t3", "name": "t3", "content": "60%"},
            ]
        )
        # Should pass - consecutive tools allowed
        errors = context.validate()
        assert all("consecutive" not in e for e in errors)

    def test_consecutive_assistant_not_allowed(self):
        """Assistant → assistant still not allowed."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "assistant", "content": "msg1"},
                {"role": "assistant", "content": "msg2"},  # Consecutive!
            ]
        )
        errors = context.validate()
        assert any(
            "consecutive messages with same role 'assistant'" in e for e in errors
        )

    def test_consecutive_user_not_allowed(self):
        """User → user still not allowed."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "msg1"},
                {"role": "user", "content": "msg2"},  # Consecutive!
            ]
        )
        errors = context.validate()
        assert any("consecutive messages with same role 'user'" in e for e in errors)

    def test_system_message_position(self):
        """System must be at index 0."""
        context = TauContext(
            [
                {"role": "user", "content": "hi"},
                {"role": "system", "content": "sys"},  # Invalid!
            ]
        )
        errors = context.validate()
        assert any(
            "system role after first message" in e
            or "has 'system' role after first message" in e
            for e in errors
        )

    def test_empty_context(self):
        """Empty context is valid."""
        context = TauContext()
        assert context.validate() == []
        assert not context.is_tool_pending()

    def test_no_tools_pending(self):
        """No tools = no pending."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ]
        )
        assert not context.is_tool_pending()
        assert context.get_pending_tool_ids() == set()

    def test_batched_tools_pending_tracking(self):
        """Track pending tools correctly."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "t1",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        },
                        {
                            "id": "t2",
                            "function": {"name": "get_temperature", "arguments": "{}"},
                        },
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t1",
                    "name": "t1",
                    "content": "sunny",
                },
            ]
        )
        assert context.get_pending_tool_ids() == {"t2"}
        assert context.is_tool_pending()

    def test_all_tools_resolved(self):
        """All tools resolved = no pending."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "t1",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        },
                        {
                            "id": "t2",
                            "function": {"name": "get_temperature", "arguments": "{}"},
                        },
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t1",
                    "name": "t1",
                    "content": "sunny",
                },
                {"role": "tool", "tool_call_id": "t2", "name": "t2", "content": "25c"},
            ]
        )
        assert context.get_pending_tool_ids() == set()
        assert not context.is_tool_pending()

    def test_validate_tool_resolution_errors(self):
        """validate_tool_resolution reports unresolved tools."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": "t1", "function": {"name": "test", "arguments": "{}"}}
                    ],
                },
            ]
        )
        errors = context.validate_tool_resolution()
        assert len(errors) == 1
        assert "unresolved tool call" in errors[0]
        assert "t1" in errors[0]

    def test_validate_tool_resolution_success(self):
        """validate_tool_resolution succeeds when all tools resolved."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": "t1", "function": {"name": "test", "arguments": "{}"}}
                    ],
                },
                {"role": "tool", "tool_call_id": "t1", "name": "t1", "content": "ok"},
            ]
        )
        errors = context.validate_tool_resolution()
        assert errors == []

    def test_complex_batched_scenario(self):
        """Complex scenario with multiple batches and tools."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Get Vienna info"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "t1",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        },
                        {
                            "id": "t2",
                            "function": {"name": "get_temperature", "arguments": "{}"},
                        },
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t1",
                    "name": "t1",
                    "content": "sunny",
                },
                {"role": "tool", "tool_call_id": "t2", "name": "t2", "content": "25c"},
                {"role": "assistant", "content": "Vienna is sunny and 25c"},
                {"role": "user", "content": "Get Berlin info"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "t3",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        },
                        {
                            "id": "t4",
                            "function": {"name": "get_temperature", "arguments": "{}"},
                        },
                        {
                            "id": "t5",
                            "function": {"name": "get_humidity", "arguments": "{}"},
                        },
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t3",
                    "name": "t3",
                    "content": "cloudy",
                },
                {"role": "tool", "tool_call_id": "t4", "name": "t4", "content": "20c"},
                {"role": "tool", "tool_call_id": "t5", "name": "t5", "content": "70%"},
                {"role": "assistant", "content": "Berlin is cloudy, 20c, 70% humidity"},
            ]
        )
        assert context.validate() == []
        assert not context.is_tool_pending()

    def test_partial_tool_resolution_in_batch(self):
        """Test partial resolution within a batch."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Do three things"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": "t1", "function": {"name": "tool1", "arguments": "{}"}},
                        {"id": "t2", "function": {"name": "tool2", "arguments": "{}"}},
                        {"id": "t3", "function": {"name": "tool3", "arguments": "{}"}},
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t1",
                    "name": "t1",
                    "content": "result1",
                },
                {
                    "role": "tool",
                    "tool_call_id": "t3",
                    "name": "t3",
                    "content": "result3",
                },
                # t2 is missing!
            ]
        )
        errors = context.validate()
        assert len(errors) > 0
        # Validation reports "unresolved" not "pending"
        assert any("unresolved" in e.lower() for e in errors)
        assert "t2" in str(errors)

    def test_tool_call_with_empty_content(self):
        """Test tool call with empty content."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": "t1", "function": {"name": "test", "arguments": "{}"}}
                    ],
                },
                {"role": "tool", "tool_call_id": "t1", "name": "t1", "content": ""},
            ]
        )
        # Empty content should be valid
        errors = context.validate()
        assert all("missing required 'content' field" not in e for e in errors)

    def test_tool_call_with_none_content(self):
        """Test tool call with None content."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {
                    "role": "user",
                    "content": "request",
                },  # Required: user message after system
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": "t1", "function": {"name": "test", "arguments": "{}"}}
                    ],
                },
                {"role": "tool", "tool_call_id": "t1", "name": "t1", "content": None},
            ]
        )
        # None content should be valid (some APIs return None)
        errors = context.validate()
        assert len(errors) == 0, f"Expected no errors, got: {errors}"

    def test_multiple_system_messages(self):
        """Test multiple system messages (only first allowed)."""
        context = TauContext(
            [
                {"role": "system", "content": "First system"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
                {"role": "system", "content": "Second system - invalid!"},
            ]
        )
        errors = context.validate()
        assert any("system" in e.lower() and "first" in e.lower() for e in errors)

    def test_tool_call_id_case_sensitivity(self):
        """Test that tool_call_id matching is case-sensitive."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": "T1", "function": {"name": "test", "arguments": "{}"}}
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "t1",
                    "name": "t1",
                    "content": "result",
                },  # Wrong case!
            ]
        )
        errors = context.validate()
        assert len(errors) > 0

    def test_empty_tool_calls_list(self):
        """Test assistant with empty tool_calls list."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "assistant", "content": "", "tool_calls": []},
            ]
        )
        # Empty tool_calls should be valid (no pending tools)
        assert not context.is_tool_pending()

    def test_tool_call_missing_function(self):
        """Test tool call with missing function field."""
        context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "assistant", "content": "", "tool_calls": [{"id": "t1"}]},
            ]
        )
        # Should have unresolved tool call error
        errors = context.validate()
        assert any("unresolved tool call" in e for e in errors)
