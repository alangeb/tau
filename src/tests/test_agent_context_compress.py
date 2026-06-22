"""Tests for agent_context_compress module - compression algorithms.

Tests:
    test_calculate_context_bytes - Helper function tests
    test_helper_functions - Helper function tests
    test_tool_pruning - Tool pruning algorithm
    test_full_reset - Full reset algorithm
    test_redact_blocks - Redact blocks algorithm
    test_last_transaction - Last transaction compression
    test_oversized_tool_redaction - New step 1 algorithm
    test_orchestrator - compress_context orchestrator
"""

from unittest.mock import Mock

from agent_context_compress import (
    compress_context,
    compress_last_transaction,
    compress_tool_pruning,
    compress_tool_pruning_full,
    compress_redact_blocks,
    compress_redact_blocks_full,
    compress_full_reset,
    compress_oversized_tool_redaction,
    _calculate_context_bytes,
    _has_unresolved_tool_calls,
)


class TestCalculateContextBytes:
    """Test _calculate_context_bytes helper function."""

    def test_empty_context(self):
        """Test with empty context."""
        assert _calculate_context_bytes([]) == 0

    def test_single_message(self):
        """Test with single message."""
        ctx = [{"role": "user", "content": "Hello"}]
        assert _calculate_context_bytes(ctx) > 0

    def test_multiple_messages(self):
        """Test with multiple messages."""
        ctx = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        total = _calculate_context_bytes(ctx)
        assert total > 0
        assert total > len(str(ctx[0]))


class TestHelperFunctions:
    """Test helper functions."""

    def test_has_unresolved_tool_calls(self):
        """Test unresolved tool call detection."""
        # Unresolved: assistant has tool_calls but no matching tool result
        assert _has_unresolved_tool_calls([
            {"role": "assistant", "tool_calls": [{"id": "1", "function": {"name": "test"}}]},
        ]) is True
        # Resolved: assistant + matching tool result
        assert _has_unresolved_tool_calls([
            {"role": "assistant", "tool_calls": [{"id": "1", "function": {"name": "test"}}]},
            {"role": "tool", "tool_call_id": "1"},
        ]) is False
        # No tool calls
        assert _has_unresolved_tool_calls([{"role": "assistant", "content": "Hi"}]) is False
        assert _has_unresolved_tool_calls([]) is False


class TestCompressToolPruning:
    """Test compress_tool_pruning algorithm."""

    def test_tool_pruning_basic(self):
        """Basic tool pruning with tool result inside 50% boundary."""
        ctx = [
            {"role": "system", "content": "System " * 20},
            {"role": "user", "content": "Task " * 20},
            {
                "role": "assistant",
                "content": "Processing " * 15,
                "tool_calls": [
                    {"id": "1", "function": {"name": "test"}, "type": "function"}
                ],
            },
            {
                "role": "tool",
                "content": "This is a very long tool result that exceeds 100 bytes and should be pruned. "
                * 10,
            },
            {"role": "assistant", "content": "Completed " * 20},
        ]
        original_size = _calculate_context_bytes(ctx)

        client = Mock()
        client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Summary"))],
            usage=Mock(prompt_tokens=10, completion_tokens=5),
        )

        result, metadata = compress_tool_pruning(ctx, client, "test-model", target_size_bytes=100)

        # Tool result should be pruned
        tool_msg = result[3]
        assert tool_msg["content"] == "COMPRESSION: CALL RESULT NO LONGER AVAILABLE"
        assert _calculate_context_bytes(result) < original_size
        # Verify metadata
        assert metadata["step_name"] == "TOOL_PRUNING"
        assert metadata["bytes_before"] == original_size
        assert metadata["bytes_after"] == _calculate_context_bytes(result)
        assert len(metadata["actions"]) > 0

    def test_tool_pruning_under_100_bytes(self):
        """Skip tools under 100 bytes."""
        ctx = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Task"},
            {
                "role": "assistant",
                "content": "Processing",
                "tool_calls": [
                    {"id": "1", "function": {"name": "test"}, "type": "function"}
                ],
            },
            {"role": "tool", "content": "Short result"},
            {"role": "assistant", "content": "Done"},
        ]
        client = Mock()
        client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Summary"))],
            usage=Mock(prompt_tokens=10, completion_tokens=5),
        )

        result, metadata = compress_tool_pruning(ctx, client, "test-model", target_size_bytes=100)

        # Should not prune (too small)
        assert result[3]["content"] == "Short result"
        assert len(metadata["actions"]) == 0


class TestCompressFullReset:
    """Test compress_full_reset algorithm."""

    def test_full_reset_basic(self):
        """Full reset scenario."""
        ctx = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Original request"},
            {
                "role": "assistant",
                "content": "Processed request",
                "tool_calls": [
                    {"id": "1", "function": {"name": "test"}, "type": "function"}
                ],
            },
            {"role": "tool", "content": "Tool result"},
            {"role": "assistant", "content": "Result processed"},
        ]

        # Create proper mock responses with tool_calls=None to avoid iteration errors
        def make_mock_response(content_text):
            return Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content=content_text,
                            tool_calls=None,
                            reasoning_content=None,
                        )
                    )
                ],
                usage=Mock(
                    prompt_tokens=10, completion_tokens=5, prompt_tokens_details=None
                ),
            )

        client = Mock()
        client.chat.completions.create.side_effect = [
            make_mock_response("Summary of conversation"),
            make_mock_response("Next steps to complete the task"),
        ]

        result, metadata = compress_full_reset(ctx, client, "test-model", target_size_bytes=100)

        # Should create minimal context
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "System prompt"
        assert result[1]["role"] == "user"
        assert "# COMPREHENSION SUMMARY" in result[1]["content"]
        assert "# NEXT STEPS" in result[1]["content"]
        assert "# ORIGINAL USER REQUEST" in result[1]["content"]
        assert "Original request" in result[1]["content"]
        # Verify metadata
        assert metadata["step_name"] == "FULL_RESET"
        assert metadata["status"] == "RESET"
        assert len(metadata["actions"]) > 0

    def test_full_reset_no_system(self):
        """Handle missing system prompt."""
        ctx = [
            {"role": "user", "content": "Request"},
            {"role": "assistant", "content": "Response"},
        ]

        def make_mock_response(content_text):
            return Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content=content_text,
                            tool_calls=None,
                            reasoning_content=None,
                        )
                    )
                ],
                usage=Mock(
                    prompt_tokens=10, completion_tokens=5, prompt_tokens_details=None
                ),
            )

        client = Mock()
        client.chat.completions.create.side_effect = [
            make_mock_response("A summary of the conversation"),
            make_mock_response("Next steps plan"),
        ]
        result, metadata = compress_full_reset(ctx, client, "test-model", target_size_bytes=100)

        # Should still work without system
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_full_reset_no_user(self):
        """Handle missing user prompt."""
        ctx = [{"role": "system", "content": "System"}]
        client = Mock()
        client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="A summary of the conversation"))],
            usage=Mock(),
        )
        result, metadata = compress_full_reset(ctx, client, "test-model", target_size_bytes=100)

        # Should return unchanged if no user prompt
        assert result == ctx
        assert metadata["status"] == "FAILED_NO_USER"


class TestCompressRedactBlocks:
    """Test compress_redact_blocks algorithm."""

    def test_redact_blocks_basic(self):
        """Basic redaction of completed blocks."""
        ctx = [
            {"role": "system", "content": "System " * 10},
            {"role": "user", "content": "Task 1 " * 20},
            {
                "role": "assistant",
                "content": "Processing 1 " * 20,
                "tool_calls": [
                    {"id": "1", "function": {"name": "test"}, "type": "function"}
                ],
            },
            {"role": "tool", "content": "Tool result 1 " * 10, "tool_call_id": "1"},
            {"role": "assistant", "content": "Completed 1 " * 20},
            {"role": "user", "content": "Task 2 " * 20},
            {
                "role": "assistant",
                "content": "Processing 2 " * 20,
                "tool_calls": [
                    {"id": "2", "function": {"name": "test"}, "type": "function"}
                ],
            },
            {"role": "tool", "content": "Tool result 2 " * 10, "tool_call_id": "2"},
            {"role": "assistant", "content": "Completed 2 " * 20},
            {"role": "user", "content": "Current task"},
            {
                "role": "assistant",
                "content": "Current work",
                "tool_calls": [
                    {"id": "3", "function": {"name": "test"}, "type": "function"}
                ],
            },
        ]

        original_size = _calculate_context_bytes(ctx)

        result, metadata = compress_redact_blocks(
            ctx, Mock(), "test-model", target_size_bytes=1000
        )

        # Should have reduced intermediate messages
        assert len(result) < len(ctx)
        assert _calculate_context_bytes(result) < original_size
        assert metadata["step_name"] == "REDACT_BLOCKS"

    def test_redact_blocks_skip_small(self):
        """Skip blocks under 300 bytes."""
        ctx = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Task"},
            {
                "role": "assistant",
                "content": "Done",
                "tool_calls": [
                    {"id": "1", "function": {"name": "test"}, "type": "function"}
                ],
            },
            {"role": "tool", "content": "Result", "tool_call_id": "1"},
            {"role": "assistant", "content": "Finish"},
        ]

        result, metadata = compress_redact_blocks(
            ctx, Mock(), "test-model", target_size_bytes=100
        )

        # Should not redact (too small)
        assert len(result) == len(ctx)
        assert len(metadata["actions"]) == 0


class TestCompressLastTransaction:
    """Test compress_last_transaction algorithm."""

    def test_last_transaction_basic(self):
        """Basic compression of last completed transaction."""
        ctx = [
            {"role": "system", "content": "System " * 20},
            {"role": "user", "content": "Task " * 20},
            {
                "role": "assistant",
                "content": "Processing " * 20,
                "tool_calls": [
                    {"id": "1", "function": {"name": "test"}, "type": "function"}
                ],
            },
            {"role": "tool", "content": "Tool result " * 20, "tool_call_id": "1"},
            {"role": "assistant", "content": "Completed " * 20},
            {"role": "user", "content": "Current task"},
            {
                "role": "assistant",
                "content": "Working...",
                "tool_calls": [
                    {"id": "2", "function": {"name": "test"}, "type": "function"}
                ],
            },
        ]

        original_size = _calculate_context_bytes(ctx)

        client = Mock()
        client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Compressed summary of previous task"))],
            usage=Mock(prompt_tokens=10, completion_tokens=5),
        )

        result, metadata = compress_last_transaction(
            ctx, client, "test-model", target_size_bytes=1000
        )

        # Should compress the last completed block
        assert _calculate_context_bytes(result) <= original_size
        assert metadata["step_name"] == "LAST_TRANSACTION"

    def test_last_transaction_no_completion(self):
        """Skip when no completed block exists (last is working)."""
        ctx = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Task"},
            {
                "role": "assistant",
                "content": "Working...",
                "tool_calls": [
                    {"id": "1", "function": {"name": "test"}, "type": "function"}
                ],
            },
        ]

        result, metadata = compress_last_transaction(
            ctx, Mock(), "test-model", target_size_bytes=100
        )

        # Should return unchanged (no completed block to compress)
        assert len(result) == len(ctx)
        assert len(metadata["actions"]) == 0


class TestOrchestrator:
    """Test compress_context orchestrator."""

    def test_orchestrator_early_success(self):
        """Test success with first algorithm."""
        ctx = [
            {"role": "system", "content": "System " * 20},
            {"role": "user", "content": "Task " * 20},
            {
                "role": "assistant",
                "content": "Processing " * 10,
                "tool_calls": [
                    {"id": "1", "function": {"name": "test"}, "type": "function"}
                ],
            },
            {
                "role": "tool",
                "content": "This is a very long tool result that will be pruned to save space. "
                * 20,
            },
            {"role": "assistant", "content": "Completed " * 20},
        ]

        client = Mock()
        client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Summary"))],
            usage=Mock(prompt_tokens=10, completion_tokens=5),
        )

        result, summary, metadata = compress_context(
            ctx, client, "test-model", target_percentage=0.3, tools=[]
        )

        # Should succeed (tool pruning should achieve target)
        assert isinstance(result, list)
        assert isinstance(summary, str)
        assert isinstance(metadata, dict)
        assert "bytes_before" in metadata
        assert "bytes_after" in metadata
        assert "algorithms_used" in metadata
        assert "ACHIEVED" in summary or "Final:" in summary


# ── Tests for new step 1: compress_oversized_tool_redaction ──


class TestCompressOversizedToolRedaction:
    """Test compress_oversized_tool_redaction algorithm."""

    def test_oversized_tool_gets_redacted(self):
        """Tool >20% of rest gets redacted when clearly in first half."""
        big_content = "X" * 5000  # 5000 bytes
        # Add enough padding before tool so it's clearly in first half
        ctx = [
            {"role": "system", "content": "System " * 100},  # ~600 bytes
            {"role": "user", "content": "Task " * 100},     # ~500 bytes
            {"role": "assistant", "content": "Early " * 100},  # ~600 bytes
            {"role": "tool", "content": big_content, "name": "bash", "tool_call_id": "1"},  # 5000 bytes
            {"role": "assistant", "content": "Done " * 100},  # ~600 bytes
            {"role": "user", "content": "Current " * 100},   # ~600 bytes
            {"role": "assistant", "content": "Working " * 100},  # ~600 bytes
        ]
        # Total ~7900 bytes, 50% boundary ~3950 bytes
        # Cumulative before tool: ~1700 bytes, after tool: ~6700 bytes
        # Tool is at ~1700 bytes, well before boundary at ~3950
        original_size = _calculate_context_bytes(ctx)
        result, metadata = compress_oversized_tool_redaction(
            ctx, Mock(), "test-model", target_size_bytes=100
        )
        # Tool should be redacted
        tool_msg = result[3]
        assert "REDACTED" in tool_msg["content"]
        assert tool_msg["name"] == "bash"  # name preserved
        assert tool_msg["tool_call_id"] == "1"  # tool_call_id preserved
        assert _calculate_context_bytes(result) < original_size
        # Verify metadata
        assert metadata["step_name"] == "OVERSIZED_TOOL_REDACTION"
        assert len(metadata["actions"]) > 0

    def test_small_tool_not_redacted(self):
        """Tool under 20% threshold is NOT redacted."""
        ctx = [
            {"role": "system", "content": "System " * 10},
            {"role": "user", "content": "Task " * 10},
            {"role": "tool", "content": "short result", "name": "grep", "tool_call_id": "1"},
            {"role": "assistant", "content": "Done " * 10},
        ]
        original_size = _calculate_context_bytes(ctx)
        result, metadata = compress_oversized_tool_redaction(
            ctx, Mock(), "test-model", target_size_bytes=100
        )
        # Tool should NOT be redacted (too small)
        assert "REDACTED" not in result[2]["content"]
        assert _calculate_context_bytes(result) == original_size
        assert len(metadata["actions"]) == 0

    def test_tool_past_50pct_boundary_not_redacted(self):
        """Tool well beyond 50% boundary is NOT redacted."""
        big_content = "Y" * 5000
        # Put the big tool clearly in the second half with lots of first-half padding
        ctx = [
            {"role": "system", "content": "System " * 200},  # ~1200 bytes
            {"role": "user", "content": "Task " * 200},      # ~1000 bytes
            {"role": "assistant", "content": "Early " * 200},  # ~1200 bytes
            {"role": "user", "content": "Mid " * 200},        # ~1000 bytes
            {"role": "assistant", "content": "MidDone " * 200},  # ~1200 bytes
            # Cumulative before tool: ~5600 bytes
            # Total context: ~10600 bytes, 50% boundary: ~5300 bytes
            # Tool is at ~5600 bytes, PAST boundary at ~5300
            {"role": "tool", "content": big_content, "name": "fetch", "tool_call_id": "2"},  # 5000 bytes
            {"role": "assistant", "content": "Late " * 200},  # ~1200 bytes
        ]
        result, metadata = compress_oversized_tool_redaction(
            ctx, Mock(), "test-model", target_size_bytes=100
        )
        # Tool should NOT be redacted (well past boundary)
        tool_msg = result[5]
        assert "REDACTED" not in tool_msg["content"]
        assert len(metadata["actions"]) == 0

    def test_verbose_vs_non_verbose(self):
        """Non-verbose produces compact output."""
        big_content = "Z" * 5000
        # Add padding so tool is clearly in first half
        ctx = [
            {"role": "system", "content": "System " * 100},  # ~600 bytes
            {"role": "user", "content": "Task " * 100},     # ~500 bytes
            {"role": "assistant", "content": "Early " * 100},  # ~600 bytes
            {"role": "tool", "content": big_content, "name": "bash", "tool_call_id": "1"},  # 5000 bytes
            {"role": "assistant", "content": "Done " * 100},  # ~600 bytes
            {"role": "user", "content": "Current " * 100},   # ~600 bytes
            {"role": "assistant", "content": "Working " * 100},  # ~600 bytes
        ]
        # Non-verbose should work without errors
        result, metadata = compress_oversized_tool_redaction(
            ctx, Mock(), "test-model", target_size_bytes=100, verbose=False
        )
        assert "REDACTED" in result[3]["content"]
        assert metadata["step_name"] == "OVERSIZED_TOOL_REDACTION"


# [REMOVED] TestOverflowInfo — OverflowInfo eliminated, truncation replaced by in-place compression.


class TestCompressToolPruningFull:
    """Test compress_tool_pruning_full — scans entire context (no 50% boundary)."""

    def _make_context_with_tool_past_boundary(self):
        """Context with heavy first-half padding and a large tool past 50%."""
        # Heavy padding in first half to push the 50% boundary early
        big_pad = "P" * 5000
        big_tool = "T" * 500  # well over 100-byte prune threshold
        return [
            {"role": "system", "content": big_pad},
            {"role": "user", "content": "Task"},
            {"role": "assistant", "content": "Processing", "tool_calls": [{"id": "1", "function": {"name": "test"}, "type": "function"}]},
            {"role": "tool", "content": "small", "tool_call_id": "1", "name": "test"},
            # Past the 50% boundary — large tool that should be pruned by _full but not boundary version
            {"role": "user", "content": "Next task"},
            {"role": "assistant", "content": "Running", "tool_calls": [{"id": "2", "function": {"name": "bash"}, "type": "function"}]},
            {"role": "tool", "content": big_tool, "tool_call_id": "2", "name": "bash"},
            {"role": "assistant", "content": "Done"},
        ]

    def test_full_prunes_past_boundary(self):
        """tool_pruning_full prunes tool output beyond 50% boundary."""
        ctx = self._make_context_with_tool_past_boundary()
        big_tool_content = ctx[6]["content"]

        result, metadata = compress_tool_pruning_full(ctx, Mock(), "test-model", target_size_bytes=100)

        # The large tool at index 6 should be pruned
        assert result[6]["content"] == "COMPRESSION: CALL RESULT NO LONGER AVAILABLE"
        assert metadata["step_name"] == "TOOL_PRUNING_FULL"
        assert len(metadata["actions"]) > 0

    def test_boundary_version_skips_past_boundary(self):
        """tool_pruning (with boundary) does NOT prune tool output beyond 50%."""
        ctx = self._make_context_with_tool_past_boundary()
        big_tool_content = ctx[6]["content"]

        result, metadata = compress_tool_pruning(ctx, Mock(), "test-model", target_size_bytes=100)

        # The large tool at index 6 should NOT be pruned (past boundary)
        assert result[6]["content"] == big_tool_content
        assert metadata["step_name"] == "TOOL_PRUNING"

    def test_full_and_boundary_identical_within_boundary(self):
        """When all content is within 50%, both versions behave the same."""
        # Small context — everything is within boundary
        big_tool = "T" * 500
        ctx = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Task"},
            {"role": "assistant", "content": "Processing", "tool_calls": [{"id": "1", "function": {"name": "test"}, "type": "function"}]},
            {"role": "tool", "content": big_tool, "tool_call_id": "1", "name": "test"},
            {"role": "assistant", "content": "Done"},
        ]

        result_boundary, _ = compress_tool_pruning(ctx, Mock(), "test-model", target_size_bytes=100)
        result_full, _ = compress_tool_pruning_full(list(ctx), Mock(), "test-model", target_size_bytes=100)

        assert result_boundary[3]["content"] == result_full[3]["content"]
        assert result_boundary[3]["content"] == "COMPRESSION: CALL RESULT NO LONGER AVAILABLE"


class TestCompressRedactBlocksFull:
    """Test compress_redact_blocks_full — scans entire context (no 50% boundary)."""

    def _make_context_with_block_past_boundary(self):
        """Context with heavy first-half padding and a completed block past 50%.

        The block must have intermediate messages (tool calls/results) to redact.
        A bare user→assistant pair has nothing to remove.
        """
        big_pad = "P" * 5000
        big_content = "B" * 400
        return [
            {"role": "system", "content": big_pad},
            {"role": "user", "content": "Early task"},
            {"role": "assistant", "content": "Early response"},
            # Past the 50% boundary — completed block WITH intermediates to redact
            {"role": "user", "content": f"Later task {big_content}"},
            {"role": "assistant", "content": "Calling tool", "tool_calls": [{"id": "2", "function": {"name": "bash"}, "type": "function"}]},
            {"role": "tool", "content": f"Tool output {big_content}", "tool_call_id": "2", "name": "bash"},
            {"role": "assistant", "content": f"Final response {big_content}"},
        ]

    def test_full_redacts_past_boundary(self):
        """redact_blocks_full redacts completed blocks beyond 50% boundary."""
        ctx = self._make_context_with_block_past_boundary()
        original_size = _calculate_context_bytes(ctx)

        result, metadata = compress_redact_blocks_full(ctx, Mock(), "test-model", target_size_bytes=100)

        # Context should be smaller (block was redacted)
        assert _calculate_context_bytes(result) < original_size
        assert metadata["step_name"] == "REDACT_BLOCKS_FULL"
        assert len(metadata["actions"]) > 0

    def test_boundary_version_skips_past_boundary(self):
        """redact_blocks (with boundary) does NOT redact blocks beyond 50%."""
        ctx = self._make_context_with_block_past_boundary()
        original_size = _calculate_context_bytes(ctx)

        result, metadata = compress_redact_blocks(ctx, Mock(), "test-model", target_size_bytes=100)

        # Context should NOT be smaller (block was skipped)
        assert _calculate_context_bytes(result) == original_size
        assert metadata["step_name"] == "REDACT_BLOCKS"
        assert len(metadata["actions"]) == 0

    def test_full_and_boundary_identical_within_boundary(self):
        """When all blocks are within 50%, both versions behave the same."""
        # Small context — everything is within boundary
        ctx = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Task A"},
            {"role": "assistant", "content": "Response A"},
            {"role": "user", "content": "Task B"},
            {"role": "assistant", "content": "Response B"},
        ]

        result_boundary, _ = compress_redact_blocks(ctx, Mock(), "test-model", target_size_bytes=100)
        result_full, _ = compress_redact_blocks_full(list(ctx), Mock(), "test-model", target_size_bytes=100)

        assert _calculate_context_bytes(result_boundary) == _calculate_context_bytes(result_full)
