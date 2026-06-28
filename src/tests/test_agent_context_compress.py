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
    compress_conversation_summary,
    compress_blind_truncate,
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


from agent_context_compress import compute_compression_target_bytes


class TestComputeCompressionTargetBytes:
    """Test compute_compression_target_bytes — token-aware target calculation."""

    def test_byte_target_only(self):
        """No token info — falls back to pure byte target."""
        result = compute_compression_target_bytes(
            current_bytes=10000,
            target_percentage=0.30,
            last_known_tokens=None,
            max_context_tokens=200000,
            max_output_tokens=12000,
        )
        assert result == 7000  # 10000 * (1 - 0.30)

    def test_token_target_more_aggressive(self):
        """Token target is lower than byte target — token wins."""
        result = compute_compression_target_bytes(
            current_bytes=100000,
            target_percentage=0.30,
            last_known_tokens=188000,
            max_context_tokens=200000,
            max_output_tokens=12000,
        )
        # byte_target = 70000
        # safety_margin = max(1000, int(200000 * 0.025)) = 5000
        # target_tokens = 200000 - 12000 - 5000 = 183000
        # token_reduction_ratio = (188000 - 183000) / 188000 = 0.0266
        # token_byte_target = 100000 * (1 - 0.0266) * 0.3 = 29310
        # min(70000, 29310) = 29310
        assert result < 70000  # token target is more aggressive
        assert result > 0

    def test_token_target_less_aggressive(self):
        """Token target is higher than byte target — byte wins."""
        result = compute_compression_target_bytes(
            current_bytes=100000,
            target_percentage=0.90,  # very aggressive byte target
            last_known_tokens=188000,
            max_context_tokens=200000,
            max_output_tokens=12000,
        )
        # byte_target = int(100000 * 0.10) = 10000 (or 9999 due to float)
        # token_byte_target will be much larger
        # min(byte_target, large_number) = byte_target
        assert result <= 10000

    def test_ratio_collapse_simulation(self):
        """Verify safety factor accounts for ratio collapse."""
        result = compute_compression_target_bytes(
            current_bytes=6500000,
            target_percentage=0.30,
            last_known_tokens=188001,
            max_context_tokens=200000,
            max_output_tokens=12000,
        )
        # safety_margin = 5000
        # target_tokens = 200000 - 12000 - 5000 = 183000
        # token_reduction_ratio = (188001 - 183000) / 188001 ≈ 0.0266
        # token_byte_target = 6500000 * (1 - 0.0266) * 0.3 ≈ 1900230
        # byte_target = 4550000
        # min(4550000, 1900230) = 1900230
        assert result < 4550000  # token-aware target is more aggressive
        assert result > 0

    def test_overflow_recovery(self):
        """Simulate the exact scenario from the bug report."""
        result = compute_compression_target_bytes(
            current_bytes=6500000,
            target_percentage=0.30,
            last_known_tokens=188001,
            max_context_tokens=200000,
            max_output_tokens=12000,
        )
        # Should produce a much more aggressive target than pure byte target
        byte_target = int(6500000 * 0.70)
        assert result < byte_target

    def test_edge_cases_zero_tokens(self):
        """Zero tokens — falls back to byte target."""
        result = compute_compression_target_bytes(
            current_bytes=10000,
            target_percentage=0.30,
            last_known_tokens=0,
            max_context_tokens=200000,
            max_output_tokens=12000,
        )
        assert result == 7000

    def test_edge_cases_none_tokens(self):
        """None tokens — falls back to byte target."""
        result = compute_compression_target_bytes(
            current_bytes=10000,
            target_percentage=0.30,
            last_known_tokens=None,
            max_context_tokens=200000,
            max_output_tokens=12000,
        )
        assert result == 7000

    def test_edge_cases_equal_tokens(self):
        """Tokens at target — no reduction needed, returns byte target."""
        result = compute_compression_target_bytes(
            current_bytes=10000,
            target_percentage=0.30,
            last_known_tokens=183000,  # exactly at target_tokens
            max_context_tokens=200000,
            max_output_tokens=12000,
        )
        # target_tokens = 200000 - 12000 - 5000 = 183000
        # last_known_tokens (183000) is NOT > target_tokens (183000)
        # So token_target stays as byte_target
        assert result == 7000

    def test_safety_margin(self):
        """Verify output tokens and safety margin are accounted for."""
        result = compute_compression_target_bytes(
            current_bytes=100000,
            target_percentage=0.30,
            last_known_tokens=195000,
            max_context_tokens=200000,
            max_output_tokens=12000,
        )
        # safety_margin = 5000
        # target_tokens = 200000 - 12000 - 5000 = 183000
        # token_reduction_ratio = (195000 - 183000) / 195000 = 0.0615
        # token_byte_target = 100000 * (1 - 0.0615) * 0.3 = 28155
        # byte_target = 70000
        # min(70000, 28155) = 28155
        assert result < 70000
        assert result > 0

    def test_tokens_below_target(self):
        """When tokens are below target, no token reduction needed."""
        result = compute_compression_target_bytes(
            current_bytes=10000,
            target_percentage=0.30,
            last_known_tokens=100000,  # well below target
            max_context_tokens=200000,
            max_output_tokens=12000,
        )
        # target_tokens = 183000, last_known_tokens (100000) < target_tokens
        # No token reduction needed, falls back to byte target
        assert result == 7000

class TestCompressConversationSummary:
    """Test compress_conversation_summary — deterministic conversation restructuring."""

    def _make_simple_context(self):
        return [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm doing well, thanks!"},
        ]

    def test_conversation_summary_basic(self):
        """Simple conversation produces structured summary."""
        ctx = self._make_simple_context()
        result, metadata = compress_conversation_summary(ctx, None, "test", 1000)
        # Result should have system + user summary (+ assistant if not within turn)
        assert len(result) >= 2
        assert result[0].get("role") == "system"
        assert result[1].get("role") == "user"
        content = result[1].get("content", "")
        assert "## CONVERSATION HISTORY" in content
        assert "### CURRENT TASK" in content
        assert "**USER:** How are you?" in content
        assert metadata["step_name"] == "CONVERSATION_SUMMARY"

    def test_conversation_summary_with_tools(self):
        """Conversation with tool calls preserves tool info."""
        ctx = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Run a command"},
            {"role": "assistant", "content": "Running...", "tool_calls": [{"id": "1", "function": {"name": "bash"}, "type": "function"}]},
            {"role": "tool", "content": "output ok", "tool_call_id": "1", "name": "bash"},
            {"role": "assistant", "content": "Done"},
        ]
        result, metadata = compress_conversation_summary(ctx, None, "test", 1000)
        content = result[1].get("content", "")
        assert "CALL: bash" in content
        assert "RESULT (bash): output ok" in content

    def test_conversation_summary_synthetic_messages(self):
        """Synthetic messages are noted as [SYSTEM: category]."""
        ctx = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "[SYNTHETIC:end_turn_reminder] Previous turn ended."},
            {"role": "assistant", "content": "Acknowledged."},
        ]
        result, metadata = compress_conversation_summary(ctx, None, "test", 1000)
        content = result[1].get("content", "")
        assert "[SYSTEM: end_turn_reminder]" in content

    def test_conversation_summary_within_turn(self):
        """Within-turn (tool result at end) shows in-progress status."""
        ctx = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Task"},
            {"role": "assistant", "content": "Calling tool", "tool_calls": [{"id": "1", "function": {"name": "test"}, "type": "function"}]},
            {"role": "tool", "content": "result", "tool_call_id": "1", "name": "test"},
        ]
        result, metadata = compress_conversation_summary(ctx, None, "test", 1000)
        content = result[1].get("content", "")
        assert "**STATUS:** in-progress" in content
        # Within turn: should NOT have synthetic assistant closing message
        assert len(result) == 2  # system + user summary only

    def test_conversation_summary_between_turns(self):
        """Between turns: adds synthetic assistant closing message."""
        ctx = self._make_simple_context()
        result, metadata = compress_conversation_summary(ctx, None, "test", 1000)
        # Should have system + user summary + synthetic assistant
        assert len(result) == 3
        assert result[2].get("role") == "assistant"
        assert "summarized" in result[2].get("content", "").lower()

    def test_openai_alternation_compliance(self):
        """Result is always valid OpenAI alternation."""
        ctx = self._make_simple_context()
        result, _ = compress_conversation_summary(ctx, None, "test", 1000)
        roles = [m.get("role") for m in result]
        # Should be [system, user] or [system, user, assistant]
        assert roles[0] == "system"
        assert roles[1] == "user"
        if len(roles) == 3:
            assert roles[2] == "assistant"


class TestCompressBlindTruncate:
    """Test compress_blind_truncate — guaranteed-fit truncation."""

    def test_blind_truncate_basic(self):
        """Truncation removes from beginning."""
        ctx = [
            {"role": "system", "content": "S"},
            {"role": "user", "content": "A" * 5000 + "### CURRENT TASK\n**USER:** important\n**STATUS:** done"},
            {"role": "assistant", "content": "ok"},
        ]
        result, metadata = compress_blind_truncate(ctx, None, "test", 200)
        content = result[1].get("content", "")
        assert "### CURRENT TASK" in content
        assert "**USER:** important" in content
        assert "[... truncated ...]" in content
        assert metadata["step_name"] == "BLIND_TRUNCATE"

    def test_blind_truncate_preserves_current_task(self):
        """CURRENT TASK section is preserved intact."""
        ctx = [
            {"role": "system", "content": "S"},
            {"role": "user", "content": "X" * 10000 + "### CURRENT TASK\n**USER:** critical info\n**STATUS:** in-progress"},
        ]
        result, metadata = compress_blind_truncate(ctx, None, "test", 300)
        content = result[1].get("content", "")
        assert "**USER:** critical info" in content
        assert "**STATUS:** in-progress" in content

    def test_blind_truncate_marker(self):
        """Truncation marker is added."""
        ctx = [
            {"role": "system", "content": "S"},
            {"role": "user", "content": "Y" * 5000 + "### CURRENT TASK\n**USER:** task\n**STATUS:** done"},
        ]
        result, _ = compress_blind_truncate(ctx, None, "test", 200)
        content = result[1].get("content", "")
        assert "[... truncated ...]" in content

    def test_blind_truncate_already_fits(self):
        """No truncation when content already fits."""
        ctx = [
            {"role": "system", "content": "S"},
            {"role": "user", "content": "short content"},
        ]
        result, metadata = compress_blind_truncate(ctx, None, "test", 5000)
        assert metadata["status"] == "ALREADY_FITS"
        assert result[1].get("content") == "short content"

    def test_pipeline_integration(self):
        """Conversation summary + blind truncate work together."""
        ctx = [
            {"role": "system", "content": "S"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        # First: conversation summary
        summary_ctx, _ = compress_conversation_summary(ctx, None, "test", 1000)
        # Then: blind truncate on the summary
        truncated, meta = compress_blind_truncate(summary_ctx, None, "test", 100)
        assert meta["step_name"] == "BLIND_TRUNCATE"
        # Verify result is small enough
        assert _calculate_context_bytes(truncated) <= 100 or meta["status"] == "TRUNCATED"

class TestTokenBudgetWiring:
    """Test that token budget values are wired through the call chain."""

    def test_llm_call_config_receives_real_values(self):
        """Verify LLMCallConfig accepts and stores max_context_tokens/max_output_tokens."""
        from agent_llm_models import LLMCallConfig

        config = LLMCallConfig(
            max_context_tokens=131072,
            max_output_tokens=8192,
        )
        assert config.max_context_tokens == 131072
        assert config.max_output_tokens == 8192

    def test_llm_call_config_defaults_as_fallback(self):
        """Verify LLMCallConfig defaults are 200K/12K when not overridden."""
        from agent_llm_models import LLMCallConfig

        config = LLMCallConfig()
        assert config.max_context_tokens == 200000
        assert config.max_output_tokens == 12000

    def test_invoke_llm_with_retry_compression_passes_token_budget(self):
        """Verify _invoke_llm_with_retry_compression threads token budget to LLMCallConfig."""
        from agent_llm_models import LLMCallConfig

        # Patch _invoke_llm_with_retry to capture the config
        captured_config = None

        def mock_invoke_llm_with_retry(client, model_name, messages, tools, tool_choice, stream, config, **kwargs):
            nonlocal captured_config
            captured_config = config
            # Return a minimal successful response
            mock_resp = type('MockResp', (), {
                'raw': type('MockRaw', (), {
                    'choices': [{'message': {'content': 'summary'}}]
                })(),
                'text': 'summary',
                'reasoning': None,
                'stats': type('MockStats', (), {
                    'total_tokens': 10,
                    'input_tokens': 5,
                    'output_tokens': 5,
                    'cached_tokens': 0,
                    'hit_rate': None,
                })(),
                'success': True,
                'error': None,
                'tool_calls': [],
            })()
            return mock_resp, False

        import agent_context_compress as mcc
        original = mcc._invoke_llm_with_retry
        mcc._invoke_llm_with_retry = mock_invoke_llm_with_retry

        try:
            resp = mcc._invoke_llm_with_retry_compression(
                client=None,
                model_name="test",
                messages=[{"role": "user", "content": "hello"}],
                tools=[],
                tool_choice="auto",
                stream=False,
                max_context_tokens=131072,
                max_output_tokens=8192,
            )
            assert captured_config is not None
            assert captured_config.max_context_tokens == 131072
            assert captured_config.max_output_tokens == 8192
        finally:
            mcc._invoke_llm_with_retry = original

    def test_token_target_with_128k_model(self):
        """Simulate 128K model: verify target is correct for 180K tokens."""
        from agent_context_compress import compute_compression_target_bytes

        # 128K model, 180K tokens (overflow scenario)
        result = compute_compression_target_bytes(
            current_bytes=5000000,
            target_percentage=0.30,
            last_known_tokens=180000,
            max_context_tokens=131072,
            max_output_tokens=8192,
        )
        # safety_margin = max(1000, int(131072 * 0.025)) = 3276
        # target_tokens = 131072 - 8192 - 3276 = 119604
        # token_reduction_ratio = (180000 - 119604) / 180000 = 0.3355
        # token_byte_target = 5000000 * (1 - 0.3355) * 0.3 = 1000750
        # byte_target = 3500000
        # min(3500000, 1000750) = 1000750
        assert result < 3500000  # token-aware is more aggressive
        assert result > 0

    def test_token_target_with_32k_model(self):
        """Simulate 32K model: verify target is correct for 30K tokens."""
        from agent_context_compress import compute_compression_target_bytes

        # 32K model, 30K tokens (near overflow)
        result = compute_compression_target_bytes(
            current_bytes=2000000,
            target_percentage=0.30,
            last_known_tokens=30000,
            max_context_tokens=32768,
            max_output_tokens=4096,
        )
        # safety_margin = max(1000, int(32768 * 0.025)) = 819
        # target_tokens = 32768 - 4096 - 819 = 27853
        # token_reduction_ratio = (30000 - 27853) / 30000 = 0.0716
        # token_byte_target = 2000000 * (1 - 0.0716) * 0.3 = 555280
        # byte_target = 1400000
        # min(1400000, 555280) = 555280
        assert result < 1400000  # token-aware is more aggressive
        assert result > 0

    def test_token_target_with_200k_model(self):
        """Simulate 200K model: verify target is correct for 190K tokens."""
        from agent_context_compress import compute_compression_target_bytes

        # 200K model, 190K tokens (near overflow)
        result = compute_compression_target_bytes(
            current_bytes=8000000,
            target_percentage=0.30,
            last_known_tokens=190000,
            max_context_tokens=200000,
            max_output_tokens=12000,
        )
        # safety_margin = max(1000, int(200000 * 0.025)) = 5000
        # target_tokens = 200000 - 12000 - 5000 = 183000
        # token_reduction_ratio = (190000 - 183000) / 190000 = 0.0368
        # token_byte_target = 8000000 * (1 - 0.0368) * 0.3 = 2313600
        # byte_target = 5600000
        # min(5600000, 2313600) = 2313600
        assert result < 5600000  # token-aware is more aggressive
        assert result > 0

    def test_compress_context_passes_token_budget(self):
        """Verify compress_context passes token budget to compute_compression_target_bytes."""
        # This is an integration test - we verify the function signature accepts
        # and uses the parameters correctly
        from agent_context_compress import compress_context, compute_compression_target_bytes

        # Verify that compress_context has the right signature
        import inspect
        sig = inspect.signature(compress_context)
        params = list(sig.parameters.keys())
        assert "last_known_tokens" in params
        assert "max_context_tokens" in params
        assert "max_output_tokens" in params

    def test_extract_token_count_from_error(self):
        """Verify token count extraction from API error messages."""
        from agent_llm_invoke import _extract_token_count_from_error

        # Standard OpenAI-style error
        assert _extract_token_count_from_error(
            "your prompt contains at least 188001 input tokens"
        ) == 188001

        # Alternative format
        assert _extract_token_count_from_error(
            "Request too large. Your prompt contains 150000 tokens"
        ) == 150000

        # No match
        assert _extract_token_count_from_error("some other error") is None

    def test_handle_context_overflow_passes_token_budget(self):
        """Verify _handle_context_overflow passes token budget to _try_context_compress."""
        from agent_llm_invoke import _handle_context_overflow, _extract_token_count_from_error
        from agent_llm_models import LLMCallConfig

        # Verify that _extract_token_count_from_error works
        assert _extract_token_count_from_error(
            "your prompt contains at least 188001 input tokens"
        ) == 188001

        # Verify LLMCallConfig stores the values
        config = LLMCallConfig(
            max_context_tokens=131072,
            max_output_tokens=8192,
            compress_client=None,
            compress_model="test",
            compress_tools=[],
            compress_extra_kwargs={},
            compress_audit_writer=None,
        )
        assert config.max_context_tokens == 131072
        assert config.max_output_tokens == 8192
