"""Test cases for /fork and /subagent commands.

Tests verify:
1. Result Propagation: Subagents return only their last assistant message to parent
2. Context Isolation: /subagent gets NO parent context, /fork gets ALL parent context
3. No Pollution: Subagents don't leak intermediate tool calls/messages to parent
4. Fork Context Preparation: Fork removes irrelevant tool calls/results
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_context import TauContext
from agent_core import TauErgon
from agent_subagent import invoke_subagent_sync, NESTING_DEPTH_THRESHOLD


def _make_mock_agent(max_context_tokens=200000, current_group_name="default"):
    """Create a minimal mock TauErgon for subagent/fork tests."""
    agent = MagicMock()
    agent.max_context_tokens = max_context_tokens
    agent.current_group_name = current_group_name
    return agent


class TestSubagentFork:
    """Test suite for /fork and /subagent commands."""

    def setup_method(self):
        """Setup before each test."""
        self.mock_llm = MagicMock()
        self.mock_llm.return_value = "Mock response"

    # =========================================================================
    # CONTEXT ISOLATION TESTS
    # =========================================================================

    def test_subagent_isolated_context(self, test_config):
        """Test subagent with isolated context (no parent context)."""
        # Mock invoke_with_tools to avoid actual LLM call
        with patch.object(TauErgon, "invoke_with_tools", return_value="Test response"):
            result = invoke_subagent_sync(
                prompt="Analyze this code",
                system_prompt="You are a code analyzer",
                parent_agent=_make_mock_agent(current_group_name="test"),
                nesting_count=0,
                config=test_config,
            )

        assert isinstance(result, str)
        assert result == "Test response"

    def test_fork_context_with_parent(self, test_config):
        """Test fork receives parent context with tool calls cleaned."""
        # Create parent context with messages
        parent_context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Analyze code"},
                {"role": "assistant", "content": "Sure"},
            ]
        )

        # Add assistant with tool calls (multiple tools)
        parent_context.append_assistant(
            None,
            [
                {"id": "fork_id", "name": "fork", "arguments": '{"task": "analyze"}'},
                {
                    "id": "read_id",
                    "name": "file_read",
                    "arguments": '{"path": "main.py"}',
                },
            ],
        )

        # Fork prepends tool result
        fork_context = TauContext(parent_context.to_list())
        fork_context.append_tool(
            "FORK MODE SUCCESSFUL: You must do: analyze", "fork_id"
        )

        # Mock invoke_with_tools
        with patch.object(TauErgon, "invoke_with_tools", return_value="Fork response"):
            result = invoke_subagent_sync(
                prompt="Continue with task: analyze",
                system_prompt="You are a test agent",
                parent_agent=_make_mock_agent(current_group_name="test"),
                nesting_count=1,
                config=test_config,
            )

        assert isinstance(result, str)
        assert result == "Fork response"

    # =========================================================================
    # FORK CONTEXT PREPARATION TESTS
    # =========================================================================

    def test_fork_prepares_clean_context(self):
        """Test fork context preparation marks pending calls and closes the turn.

        prepare_fork_context resolves *pending* tool IDs (those without matching
        tool results) by appending marker tool results:
        - The fork's own call gets the FORK marker (identity + task signal).
        - Sibling pending calls get the PENDING marker (deferred, not failed).
        Already-resolved tool calls are left untouched.
        Finally an assistant closure message is appended.
        """
        # Create parent context with multiple tools
        parent_context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Analyze code"},
                {"role": "assistant", "content": "Sure"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "fork_id",
                            "name": "fork",
                            "arguments": '{"task": "analyze"}',
                        },
                        {
                            "id": "read_id",
                            "name": "file_read",
                            "arguments": '{"path": "main.py"}',
                        },
                        {
                            "id": "grep_id",
                            "name": "grep",
                            "arguments": '{"pattern": "test"}',
                        },
                    ],
                },
                {"role": "tool", "tool_call_id": "read_id", "content": "file content"},
                {"role": "tool", "tool_call_id": "grep_id", "content": "grep result"},
            ]
        )

        # Prepare fork context (modifies in-place)
        # Only fork_id is pending → gets FORK marker, then closure assistant appended
        parent_context.prepare_fork_context(task="analyze", fork_tool_call_id="fork_id")

        # 2 existing tool messages (read_id, grep_id) + 1 new FORK (fork_id) = 3 total
        tool_msgs = [m for m in parent_context if m.get("role") == "tool"]
        assert len(tool_msgs) == 3, f"Expected 3 tool results, got {len(tool_msgs)}"

        # The new tool result should contain the FORK marker
        fork_msgs = [m for m in tool_msgs if "[FORK:" in m.get("content", "")]
        assert (
            len(fork_msgs) == 1
        ), f"Expected 1 FORK marker result, got {len(fork_msgs)}"
        assert fork_msgs[0].get("tool_call_id") == "fork_id"

        # Last message should be the closure assistant
        assert parent_context[-1].get("role") == "assistant"
        assert "forking to:" in parent_context[-1].get("content", "")

    def test_fork_preserves_parent_continuation(self):
        """Test fork preparation on an already-closed context is a no-op.

        When the context is already in a valid terminal state (all tool calls
        resolved, last message is assistant), prepare_fork_context does not add
        new messages. close_turn() is idempotent, but merge_consecutive_assistants()
        merges the two consecutive assistant messages (indices 2 and 3), reducing
        the count from 6 to 5.
        """
        # Create parent context with continuation after fork (all calls resolved)
        parent_context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Analyze code"},
                {"role": "assistant", "content": "Sure"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "fork_id",
                            "name": "fork",
                            "arguments": '{"task": "analyze"}',
                        },
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "fork_id",
                    "content": "FORK MODE SUCCESSFUL...",
                },
                {"role": "assistant", "content": "Parent continued after fork"},
            ]
        )

        # Prepare fork context — already closed, so close_turn is idempotent (no-op)
        # but merge_consecutive_assistants() merges the two consecutive assistant
        # messages (indices 2 and 3), reducing count from 6 to 5
        parent_context.prepare_fork_context("analyze")

        # Context goes from 6 to 5 because consecutive assistants are merged
        assert (
            len(parent_context) == 5
        ), f"Expected 5 messages (merged assistants), got {len(parent_context)}"

        # Last message is still the original assistant
        assert parent_context[-1].get("content") == "Parent continued after fork"

    # =========================================================================
    # NESTING DEPTH TESTS
    # =========================================================================

    def test_nesting_depth_limit(self, test_config):
        """Test nesting depth enforcement."""
        mock_agent = _make_mock_agent(current_group_name="test")

        # Should work at depth 0
        with patch.object(TauErgon, "invoke_with_tools", return_value="Response"):
            result1 = invoke_subagent_sync(
                prompt="Task 1",
                system_prompt="Test",
                parent_agent=mock_agent,
                nesting_count=0,
                config=test_config,
            )
            assert isinstance(result1, str)

        # Should work at depth 1
        with patch.object(TauErgon, "invoke_with_tools", return_value="Response"):
            result2 = invoke_subagent_sync(
                prompt="Task 2",
                system_prompt="Test",
                parent_agent=mock_agent,
                nesting_count=1,
                config=test_config,
            )
            assert isinstance(result2, str)

        # Should return error string at depth 2 (tools/fork.py returns error string)
        from tools.fork import run as fork_run
        from tools.subagent import run as subagent_run

        mock_agent.nesting_count = NESTING_DEPTH_THRESHOLD
        result = fork_run(task="Task 3", agent=mock_agent, tool_call_id="test")
        assert isinstance(result, str)
        assert "Maximum nesting depth" in result or "ERROR" in result

        mock_agent.nesting_count = NESTING_DEPTH_THRESHOLD
        result = subagent_run(task="Task 3", agent=mock_agent)
        assert isinstance(result, str)
        assert "Maximum nesting depth" in result or "ERROR" in result

    # =========================================================================
    # FORK TOOL INTEGRATION TESTS
    # =========================================================================

    def test_fork_tool_integration(self, test_config):
        """Test fork.py calling invoke_fork_sync with prepared context."""
        from tools.fork import run

        # Create mock agent
        agent = MagicMock()
        agent.base_url = "http://test:8000/v1"
        agent.model_name = "test-model"
        agent.max_context_tokens = 200000
        agent.nesting_count = 0
        agent.current_group_name = "test"
        agent.config = test_config

        # Create parent context
        agent.context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Test task"},
            ]
        )

        # Unified path: all forks use invoke_with_tools (adds user message + loops)
        with patch.object(TauErgon, "invoke_with_tools", return_value="Fork output"):
            result = run(
                task="analyze code",
                agent=agent,
                tool_call_id="fork-123",
            )

        assert isinstance(result, str)
        assert result == "Fork output"

    def test_fork_tool_cli_integration(self, test_config):
        """Test fork.py calling invoke_fork_sync via CLI /fork command."""
        from tools.fork import run

        # Create mock agent
        agent = MagicMock()
        agent.base_url = "http://test:8000/v1"
        agent.model_name = "test-model"
        agent.max_context_tokens = 200000
        agent.nesting_count = 0
        agent.current_group_name = "test"
        agent.config = test_config

        # Create parent context
        agent.context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Test task"},
            ]
        )

        # Mock invoke_with_tools (fork without tool_call_id uses this)
        with patch.object(
            TauErgon, "invoke_with_tools", return_value="Fork CLI output"
        ):
            result = run(
                task="analyze code",
                agent=agent,
                tool_call_id=None,
            )

        assert isinstance(result, str)
        assert result == "Fork CLI output"

    def test_subagent_tool_integration(self, test_config):
        """Test subagent.py calling invoke_subagent_sync."""
        from tools.subagent import run

        # Create mock agent
        agent = MagicMock()
        agent.base_url = "http://test:8000/v1"
        agent.model_name = "test-model"
        agent.max_context_tokens = 200000
        agent.nesting_count = 0
        agent.current_group_name = "test"
        agent.config = test_config

        # Mock invoke_with_tools (subagent tool calls invoke_with_tools on the new subagent)
        with patch.object(
            TauErgon, "invoke_with_tools", return_value="Subagent output"
        ):
            result = run(
                task="analyze code",
                agent=agent,
            )

        assert isinstance(result, str)
        assert result == "Subagent output"

    # =========================================================================
    # PREPARE FORK CONTEXT — MARKER COVERAGE TESTS
    # =========================================================================

    def test_pending_sibling_markers(self):
        """Pending sibling tool calls get PENDING marker; fork call gets FORK marker.

        When the assistant made multiple tool calls and only some have results,
        prepare_fork_context must mark the fork call with FORK and all other
        pending calls with PENDING.
        """
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Do things"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "fork_id",
                            "type": "function",
                            "function": {"name": "fork", "arguments": "{}"},
                        },
                        {
                            "id": "read_id",
                            "type": "function",
                            "function": {"name": "read", "arguments": "{}"},
                        },
                        {
                            "id": "grep_id",
                            "type": "function",
                            "function": {"name": "grep", "arguments": "{}"},
                        },
                    ],
                },
                # read_id already resolved, fork_id and grep_id are pending
                {"role": "tool", "tool_call_id": "read_id", "content": "file content"},
            ]
        )

        ctx.prepare_fork_context(task="analyze", fork_tool_call_id="fork_id")

        tool_msgs = [m for m in ctx if m.get("role") == "tool"]
        # 1 existing (read_id) + 2 new markers (fork_id, grep_id) = 3
        assert len(tool_msgs) == 3

        fork_msgs = [m for m in tool_msgs if "[FORK:" in m.get("content", "")]
        pending_msgs = [m for m in tool_msgs if "[PENDING:" in m.get("content", "")]

        assert len(fork_msgs) == 1, f"Expected 1 FORK marker, got {len(fork_msgs)}"
        assert fork_msgs[0].get("tool_call_id") == "fork_id"

        assert (
            len(pending_msgs) == 1
        ), f"Expected 1 PENDING marker, got {len(pending_msgs)}"
        assert pending_msgs[0].get("tool_call_id") == "grep_id"

    def test_fork_tool_call_id_not_in_pending_warns(self):
        """If fork_tool_call_id is set but not among pending calls, warn and continue.

        The fork call will not receive the FORK marker — all pending calls get
        PENDING instead.  A validation warning is emitted.
        """
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Do things"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "read_id",
                            "type": "function",
                            "function": {"name": "read", "arguments": "{}"},
                        },
                        {
                            "id": "grep_id",
                            "type": "function",
                            "function": {"name": "grep", "arguments": "{}"},
                        },
                    ],
                },
            ]
        )

        with patch("agent_context._emit_context_validation_warning") as mock_warn:
            ctx.prepare_fork_context(task="analyze", fork_tool_call_id="nonexistent_id")

        # Warning was emitted
        assert mock_warn.called, "Expected warning for missing fork_tool_call_id"
        warn_args = mock_warn.call_args[0]
        assert any("nonexistent_id" in str(a) for a in warn_args)

        # All pending calls got PENDING marker (none got FORK)
        tool_msgs = [m for m in ctx if m.get("role") == "tool"]
        fork_msgs = [m for m in tool_msgs if "[FORK:" in m.get("content", "")]
        pending_msgs = [m for m in tool_msgs if "[PENDING:" in m.get("content", "")]

        assert len(fork_msgs) == 0, "No FORK marker when id not in pending"
        assert len(pending_msgs) == 2, "Both pending calls got PENDING marker"

    def test_fork_tool_call_id_not_in_pending_no_pending_warns(self):
        """If fork_tool_call_id is set but there are no pending calls at all, warn.

        This covers the edge case where the context is already fully resolved
        but a fork_tool_call_id is still provided.
        """
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Do things"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "read_id",
                            "type": "function",
                            "function": {"name": "read", "arguments": "{}"},
                        },
                    ],
                },
                {"role": "tool", "tool_call_id": "read_id", "content": "file content"},
                {"role": "assistant", "content": "Done."},
            ]
        )

        with patch("agent_context._emit_context_validation_warning") as mock_warn:
            ctx.prepare_fork_context(task="analyze", fork_tool_call_id="some_id")

        # Warning emitted for missing fork_tool_call_id with no pending calls
        assert mock_warn.called
        warn_args = mock_warn.call_args[0]
        assert any("no pending calls" in str(a) for a in warn_args)

    def test_prepare_fork_context_idempotency_guard(self):
        """Calling prepare_fork_context twice handles pending calls correctly.

        After the first call, the pending tool call is resolved (marked as FORK).
        The second call finds no pending calls and warns that the fork_tool_call_id
        is not found, but still closes the turn.
        """
        ctx = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Do things"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "fork_id",
                            "type": "function",
                            "function": {"name": "fork", "arguments": "{}"},
                        },
                    ],
                },
            ]
        )

        # First call — should prepare normally
        ctx.prepare_fork_context(task="analyze", fork_tool_call_id="fork_id")
        tool_msgs_after_first = len([m for m in ctx if m.get("role") == "tool"])
        assert tool_msgs_after_first == 1  # one FORK marker

        # Second call — no pending calls remain, so it warns and adds closure only
        with patch("agent_context._emit_context_validation_warning") as mock_warn:
            ctx.prepare_fork_context(task="analyze2", fork_tool_call_id="fork_id")

        # Warning should be emitted about fork_tool_call_id not found
        assert mock_warn.called, "Expected warning for fork_tool_call_id not in pending"

        # No new tool messages added (only assistant closure was added by close_turn)
        tool_msgs_after_second = len([m for m in ctx if m.get("role") == "tool"])
        assert (
            tool_msgs_after_second == 1
        ), "Second call should not add duplicate tool markers when no pending calls"

    # =========================================================================
    # ADDITIONAL EDGE CASE TESTS
    # =========================================================================

    def test_fork_with_multiple_pending_calls(self):
        """Test fork with 5+ pending tool calls - all should be marked correctly."""
        ctx = TauContext(
            [
                {"role": "system", "content": "System"},
                {"role": "user", "content": "User"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call1",
                            "type": "function",
                            "function": {"name": "tool1", "arguments": "{}"},
                        },
                        {
                            "id": "call2",
                            "type": "function",
                            "function": {"name": "tool2", "arguments": "{}"},
                        },
                        {
                            "id": "call3",
                            "type": "function",
                            "function": {"name": "tool3", "arguments": "{}"},
                        },
                        {
                            "id": "call4",
                            "type": "function",
                            "function": {"name": "tool4", "arguments": "{}"},
                        },
                        {
                            "id": "call5",
                            "type": "function",
                            "function": {"name": "tool5", "arguments": "{}"},
                        },
                    ],
                },
            ]
        )

        # Prepare fork with call3 as the fork call
        ctx.prepare_fork_context(task="task1", fork_tool_call_id="call3")

        # Verify all pending calls are marked
        tool_messages = [m for m in ctx if m.get("role") == "tool"]
        assert (
            len(tool_messages) == 5
        ), f"Expected 5 tool messages, got {len(tool_messages)}"

        # Verify fork call has FORK marker
        fork_msg = next(
            (m for m in tool_messages if m.get("tool_call_id") == "call3"), None
        )
        assert fork_msg is not None
        assert "[FORK:" in fork_msg["content"]
        assert "task1" in fork_msg["content"]

        # Verify other calls have PENDING markers
        for call_id in ["call1", "call2", "call4", "call5"]:
            msg = next(
                (m for m in tool_messages if m.get("tool_call_id") == call_id), None
            )
            assert msg is not None
            assert "[PENDING:" in msg["content"]

    def test_fork_with_no_pending_calls(self):
        """Test fork when all tool calls are already resolved."""
        ctx = TauContext(
            [
                {"role": "system", "content": "System"},
                {"role": "user", "content": "User"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call1",
                            "type": "function",
                            "function": {"name": "test", "arguments": "{}"},
                        }
                    ],
                },
                {"role": "tool", "tool_call_id": "call1", "content": "result"},
            ]
        )

        # Should not raise error even with no pending calls
        ctx.prepare_fork_context(task="task1", fork_tool_call_id="call1")

        # Context should be closed properly
        assert ctx[-1]["role"] == "assistant"
        assert "forking to:" in ctx[-1]["content"]

        # Fork metadata should be set (if using new metadata system)
        if hasattr(ctx, "get_fork_metadata"):
            metadata = ctx.get_fork_metadata()
            assert metadata["fork_task"] == "task1"

    def test_fork_metadata_isolation(self):
        """Test that fork metadata is properly isolated between parent and child."""
        import copy

        parent_ctx = TauContext(
            [
                {"role": "system", "content": "System"},
                {"role": "user", "content": "User"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call1",
                            "type": "function",
                            "function": {"name": "test", "arguments": "{}"},
                        }
                    ],
                },
            ]
        )

        # Set parent fork metadata
        if hasattr(parent_ctx, "set_fork_metadata"):
            parent_ctx.set_fork_metadata(
                fork_tool_call_id="call1", fork_task="parent task"
            )
            parent_ctx.get_fork_metadata()

            # Create fork context as deep copy
            fork_ctx = TauContext(copy.deepcopy(parent_ctx.to_list()))

            # Fork should have fresh metadata (not inherited)
            fork_metadata = fork_ctx.get_fork_metadata()
            assert fork_metadata["fork_tool_call_id"] is None
            assert fork_metadata["fork_task"] is None
            assert len(fork_metadata["pending_tool_ids"]) == 0

            # Prepare fork with new metadata
            fork_ctx.prepare_fork_context(task="fork task", fork_tool_call_id="call1")
            new_fork_metadata = fork_ctx.get_fork_metadata()

            # Parent metadata should be unchanged
            parent_metadata_after = parent_ctx.get_fork_metadata()
            assert parent_metadata_after["fork_task"] == "parent task"

            # Fork should have its own metadata
            assert new_fork_metadata["fork_task"] == "fork task"
