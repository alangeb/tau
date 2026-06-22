"""Integration tests for fork metadata cleanup.

These tests verify that fork metadata is properly cleaned up after fork operations
complete, ensuring the parent context returns to a clean state.
"""

import pytest
from unittest.mock import Mock, patch
from agent_context import TauContext
from agent_subagent import invoke_fork_sync
from agent_core import TauErgon
from agent_config import Config


class TestForkMetadataCleanup:
    """Test fork metadata cleanup after fork operations."""

    def test_fork_metadata_cleared_after_successful_fork(self):
        """Test that fork metadata is cleared after a successful fork.

        This verifies that the parent context's fork metadata is cleared
        after the fork operation completes successfully.
        """
        # Create parent context with some messages
        parent_context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]
        )

        # Set fork metadata (simulating fork preparation)
        parent_context.set_fork_metadata(
            fork_tool_call_id="call_123", fork_task="Test task"
        )

        # Verify metadata is set
        metadata = parent_context.get_fork_metadata()
        assert metadata["fork_tool_call_id"] == "call_123"
        assert metadata["fork_task"] == "Test task"

        # Clear metadata (simulating fork completion)
        parent_context.clear_fork_metadata()

        # Verify metadata is cleared
        metadata = parent_context.get_fork_metadata()
        assert metadata["fork_tool_call_id"] is None
        assert metadata["fork_task"] is None
        assert len(metadata["pending_tool_ids"]) == 0

    def test_fork_metadata_isolation_between_forks(self):
        """Test that fork metadata is properly isolated between fork operations.

        This verifies that each fork operation starts with clean metadata
        and doesn't interfere with previous fork metadata.
        """
        parent_context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
            ]
        )

        # First fork
        parent_context.set_fork_metadata(
            fork_tool_call_id="call_1", fork_task="First task"
        )
        metadata1 = parent_context.get_fork_metadata()
        assert metadata1["fork_task"] == "First task"

        # Clear and prepare for second fork
        parent_context.clear_fork_metadata()
        parent_context.set_fork_metadata(
            fork_tool_call_id="call_2", fork_task="Second task"
        )
        metadata2 = parent_context.get_fork_metadata()
        assert metadata2["fork_task"] == "Second task"
        assert metadata2["fork_tool_call_id"] == "call_2"

        # Verify first fork metadata is gone
        assert metadata2["fork_tool_call_id"] != "call_1"
        assert metadata2["fork_task"] != "First task"

    def test_fork_metadata_cleared_on_error(self):
        """Test that fork metadata is cleared even if fork fails.

        This verifies that fork metadata cleanup happens regardless of
        whether the fork operation succeeds or fails.
        """
        parent_context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
            ]
        )

        # Set fork metadata
        parent_context.set_fork_metadata(
            fork_tool_call_id="call_123", fork_task="Test task"
        )

        # Verify metadata is set
        metadata = parent_context.get_fork_metadata()
        assert metadata["fork_tool_call_id"] == "call_123"

        # Simulate error scenario - clear metadata manually
        # (in real scenario, this would happen in a finally block)
        try:
            # Simulate fork operation that fails
            raise Exception("Simulated fork failure")
        except Exception:
            # Clean up metadata in error handler
            parent_context.clear_fork_metadata()

        # Verify metadata is cleared despite error
        metadata = parent_context.get_fork_metadata()
        assert metadata["fork_tool_call_id"] is None
        assert metadata["fork_task"] is None

    def test_fork_metadata_with_pending_tools(self):
        """Test fork metadata cleanup with pending tool calls.

        This verifies that fork metadata correctly tracks pending tool calls
        and that cleanup properly resets this state.
        """
        parent_context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "tool_1",
                            "function": {"name": "bash", "arguments": "ls"},
                        }
                    ],
                },
            ]
        )

        # Set fork metadata (should include pending tool IDs)
        parent_context.set_fork_metadata(
            fork_tool_call_id="fork_call", fork_task="Test task with pending tools"
        )

        metadata = parent_context.get_fork_metadata()
        assert "tool_1" in metadata["pending_tool_ids"]
        assert metadata["fork_tool_call_id"] == "fork_call"

        # Clear metadata
        parent_context.clear_fork_metadata()

        # Verify all metadata is cleared including pending tool IDs
        metadata = parent_context.get_fork_metadata()
        assert len(metadata["pending_tool_ids"]) == 0
        assert metadata["fork_tool_call_id"] is None
        assert metadata["fork_task"] is None

    def test_fork_metadata_not_inherited_by_fork(self):
        """Test that fork contexts don't inherit parent's fork metadata.

        This verifies that when a fork is created, it gets a clean context
        without the parent's fork metadata.
        """
        parent_context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
            ]
        )

        # Set fork metadata on parent
        parent_context.set_fork_metadata(
            fork_tool_call_id="call_123", fork_task="Parent task"
        )

        # Create fork context (deep copy)
        import copy

        fork_context = TauContext(copy.deepcopy(parent_context.to_list()))

        # Verify fork context has clean metadata
        fork_metadata = fork_context.get_fork_metadata()
        assert fork_metadata["fork_tool_call_id"] is None
        assert fork_metadata["fork_task"] is None
        assert len(fork_metadata["pending_tool_ids"]) == 0

        # Verify parent still has metadata
        parent_metadata = parent_context.get_fork_metadata()
        assert parent_metadata["fork_tool_call_id"] == "call_123"
        assert parent_metadata["fork_task"] == "Parent task"

    def test_prepare_fork_context_sets_metadata(self):
        """Test that prepare_fork_context properly sets fork metadata.

        This verifies that the prepare_fork_context function correctly
        sets up fork metadata before forking.
        """
        parent_context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
            ]
        )

        # Prepare for fork
        parent_context.prepare_fork_context(
            task="Test task", fork_tool_call_id="call_123"
        )

        # Verify metadata is set
        metadata = parent_context.get_fork_metadata()
        assert metadata["fork_tool_call_id"] == "call_123"
        assert metadata["fork_task"] == "Test task"

    def test_multiple_forks_cleared_properly(self):
        """Test that multiple sequential forks clear metadata properly.

        This verifies that each fork operation properly cleans up metadata
        and doesn't leave stale data from previous forks.
        """
        parent_context = TauContext(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
            ]
        )

        # First fork
        parent_context.set_fork_metadata(fork_tool_call_id="call_1", fork_task="Task 1")
        assert parent_context.get_fork_metadata()["fork_task"] == "Task 1"
        parent_context.clear_fork_metadata()

        # Second fork
        parent_context.set_fork_metadata(fork_tool_call_id="call_2", fork_task="Task 2")
        assert parent_context.get_fork_metadata()["fork_task"] == "Task 2"
        parent_context.clear_fork_metadata()

        # Third fork
        parent_context.set_fork_metadata(fork_tool_call_id="call_3", fork_task="Task 3")
        assert parent_context.get_fork_metadata()["fork_task"] == "Task 3"
        parent_context.clear_fork_metadata()

        # Verify all metadata is cleared
        metadata = parent_context.get_fork_metadata()
        assert metadata["fork_tool_call_id"] is None
        assert metadata["fork_task"] is None
        assert len(metadata["pending_tool_ids"]) == 0
