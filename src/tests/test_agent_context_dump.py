"""Tests for TauContext.dump() method and trace mode."""

from agent_context import TauContext


class TestDumpMethod:
    """Test TauContext.dump() method."""

    def test_dump_summary(self):
        """Test summary mode output."""
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ]
        )
        output = ctx.dump(mode="summary", max_tokens=1000, exact_tokens=50)
        assert "CONTEXT SUMMARY" in output
        assert "3 messages" in output
        assert "50" in output  # exact token count
        assert "system" in output.lower() or "[SYST]" in output
        assert "user" in output.lower() or "[USER]" in output
        assert "assistant" in output.lower() or "[ASSI]" in output

    def test_dump_full(self):
        """Test full mode output."""
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello world"},
                {"role": "assistant", "content": "Hi there, how can I help?"},
            ]
        )
        output = ctx.dump(mode="full")
        assert "CONTEXT (3 messages)" in output
        assert "Hello world" in output
        assert "Hi there, how can I help?" in output

    def test_dump_user(self):
        """Test user mode output."""
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
                {"role": "user", "content": "Goodbye"},
            ]
        )
        output = ctx.dump(mode="user")
        assert "USER MESSAGES ONLY (2 messages)" in output
        assert "Hello" in output
        assert "Goodbye" in output
        assert "assistant" not in output.lower() or "USER" in output

    def test_dump_tool(self):
        """Test tool mode output."""
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "tc1",
                            "function": {
                                "name": "grep",
                                "arguments": '{"pattern": "test"}',
                            },
                        },
                    ],
                },
                {"role": "tool", "tool_call_id": "tc1", "content": "found results"},
            ]
        )
        output = ctx.dump(mode="tool")
        assert "TOOL MESSAGES ONLY (1 messages)" in output
        assert "found results" in output

    def test_dump_assistant(self):
        """Test assistant mode output."""
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
                {"role": "user", "content": "Bye"},
                {"role": "assistant", "content": "Goodbye!"},
            ]
        )
        output = ctx.dump(mode="assistant")
        assert "ASSISTANT MESSAGES ONLY (2 messages)" in output
        assert "Hi there" in output
        assert "Goodbye!" in output

    def test_dump_invalid_mode(self):
        """Test invalid mode returns error message."""
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
            ]
        )
        output = ctx.dump(mode="invalid")
        assert "Invalid mode" in output


class TestDumpTrace:
    """Test TauContext.dump(mode='trace') method."""

    def test_dump_trace_basic(self):
        """Test trace mode with basic messages."""
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ]
        )
        output = ctx.dump(mode="trace")
        assert "CONTEXT TRACE" in output
        assert "[SYST]" in output
        assert "[USER]" in output
        assert "[ASSI]" in output
        assert "END TRACE" in output

    def test_dump_trace_with_tool_calls(self):
        """Test trace mode shows full tool calls with IDs."""
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Search for something"},
                {
                    "role": "assistant",
                    "content": "Let me search",
                    "tool_calls": [
                        {
                            "id": "tc1",
                            "function": {
                                "name": "grep",
                                "arguments": '{"pattern": "test"}',
                            },
                        },
                    ],
                },
                {"role": "tool", "tool_call_id": "tc1", "content": "found 5 results"},
            ]
        )
        output = ctx.dump(mode="trace")
        assert "CONTEXT TRACE" in output
        # Tool call should show name and id
        assert "grep" in output
        assert "tc1" in output
        # Result link should be shown
        assert "found 5 results" in output

    def test_dump_trace_pending_tool_calls(self):
        """Test trace mode shows pending tool calls."""
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Do two things"},
                {
                    "role": "assistant",
                    "content": "Doing both",
                    "tool_calls": [
                        {
                            "id": "tc1",
                            "function": {
                                "name": "grep",
                                "arguments": '{"pattern": "test"}',
                            },
                        },
                        {
                            "id": "tc2",
                            "function": {
                                "name": "glob",
                                "arguments": '{"pattern": "*.py"}',
                            },
                        },
                    ],
                },
                {"role": "tool", "tool_call_id": "tc1", "content": "grep result"},
            ]
        )
        output = ctx.dump(mode="trace")
        assert "PENDING TOOL CALLS" in output
        assert "tc2" in output
        # tc1 should show resolved result
        assert "grep result" in output
        # tc2 should show PENDING
        assert "PENDING" in output

    def test_dump_trace_tool_call_id_linkage(self):
        """Test trace mode links tool_call_id to tool result."""
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Call a tool"},
                {
                    "role": "assistant",
                    "content": "Calling",
                    "tool_calls": [
                        {
                            "id": "abc123",
                            "function": {
                                "name": "bash",
                                "arguments": '{"cmd": "ls -la"}',
                            },
                        },
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "abc123",
                    "content": "file1.txt\nfile2.txt",
                },
            ]
        )
        output = ctx.dump(mode="trace")
        # The tool call id should appear in both the assistant section and tool section
        assert "abc123" in output
        # The tool call name should be shown
        assert "bash" in output
        # The result should be linked
        assert "file1.txt" in output

    def test_dump_trace_shows_all_messages(self):
        """Test trace mode shows all messages from start to end."""
        messages = [{"role": "system", "content": "You are helpful"}]
        for i in range(5):
            messages.append({"role": "user", "content": f"User message {i}"})
            messages.append({"role": "assistant", "content": f"Assistant message {i}"})
        ctx = TauContext(messages)
        output = ctx.dump(mode="trace")
        # Trace shows ALL messages
        assert "User message 0" in output
        assert "User message 4" in output
        assert "Assistant message 4" in output
        assert "END TRACE" in output

    def test_dump_trace_content_truncation(self):
        """Test trace mode truncates content to 200 chars."""
        long_content = "x" * 500
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": long_content},
            ]
        )
        output = ctx.dump(mode="trace")
        # Content should be truncated to 200 chars
        assert "..." in output
        assert long_content not in output

    def test_dump_trace_no_tool_calls(self):
        """Test trace mode with assistant message without tool calls."""
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there, how can I help you today?"},
            ]
        )
        output = ctx.dump(mode="trace")
        assert "[ASSI]" in output
        assert "Hi there" in output
        # Should not show tool call sections
        assert "└─" not in output

    def test_dump_trace_validation_errors_shown(self):
        """Test trace mode shows validation errors."""
        ctx = TauContext(
            [
                {"role": "user", "content": "Hello"},  # No system message
                {"role": "user", "content": "Bye"},  # Consecutive user
            ]
        )
        output = ctx.dump(mode="trace")
        assert "VALIDATION ERRORS" in output
        assert "consecutive" in output.lower() or "system" in output.lower()


class TestEmitContextValidationWarning:
    """Test that _emit_context_validation_warning prints the warning without auto-dumping trace."""

    def test_emit_warning_shows_warning_only(self):
        """Test that _emit_context_validation_warning outputs the warning but not a trace dump."""
        from agent_context import _emit_context_validation_warning
        from unittest.mock import patch, MagicMock

        with patch("agent_context.context_validation_warning", new=MagicMock()) as mock_warn:
            _emit_context_validation_warning("Test warning message")

            # Verify context_validation_warning was called
            mock_warn.assert_called_once()
