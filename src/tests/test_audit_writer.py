"""Unit and integration tests for AuditWriter (simplified, no-thread version).

Tests cover:
- Buffer → flush → disk roundtrip
- Batch flushing
- Empty buffer handling
- Append mode preservation
- Multi-line content formatting
- Silent disk failure handling
- Tool call counter
- Session start logging
- Full turn cycle integration
- Regression: no threads spawned
"""

import threading
from pathlib import Path

import pytest

from agent_session import AuditWriter


@pytest.fixture
def audit_file(temp_dir):
    """Provide a temporary audit file path."""
    return temp_dir / "test.audit"


class TestAuditWriterBasic:
    """Basic unit tests for AuditWriter."""

    def test_flush_writes_buffer(self, audit_file):
        """Verify flush writes buffer to disk."""
        writer = AuditWriter(audit_file)
        writer.user("hello world")
        assert not audit_file.exists()  # Not flushed yet
        writer.flush()
        assert audit_file.exists()
        assert "hello world" in audit_file.read_text()

    def test_batch_flush(self, audit_file):
        """Verify multiple records batch into single flush."""
        writer = AuditWriter(audit_file)
        writer.user("msg1")
        writer.user("msg2")
        writer.tool_call("id1", "bash", {}, "bash", {}, [])
        writer.flush()
        content = audit_file.read_text()
        assert content.count("USER") == 2
        assert content.count("TOOL_CALL") == 1

    def test_flush_empty_buffer(self, audit_file):
        """Verify flush on empty buffer doesn't create file."""
        writer = AuditWriter(audit_file)
        writer.flush()
        assert not audit_file.exists()

    def test_append_preserves_data(self, audit_file):
        """Verify append mode preserves previous flushes."""
        writer = AuditWriter(audit_file)
        writer.user("first")
        writer.flush()
        writer.user("second")
        writer.flush()
        content = audit_file.read_text()
        assert "first" in content
        assert "second" in content

    def test_multiline_tool_result(self, audit_file):
        """Verify multi-line content is properly formatted."""
        writer = AuditWriter(audit_file)
        writer.tool_result("id1", "ok", 100.0, "line1\nline2\nline3", 20)
        writer.flush()
        content = audit_file.read_text()
        assert "  |   line1" in content
        assert "  |   line2" in content
        assert "  |   line3" in content

    def test_silent_disk_failure(self, audit_file):
        """Verify disk write failures are silently ignored."""
        writer = AuditWriter(audit_file)
        writer.user("test")
        # Create file and make it unwritable
        audit_file.write_text("")
        audit_file.chmod(0o000)
        writer.flush()  # Should not raise
        # Restore permissions for cleanup
        audit_file.chmod(0o644)

    def test_tool_call_counter(self, audit_file):
        """Verify tool_call increments counter."""
        writer = AuditWriter(audit_file)
        assert writer.total_tool_calls == 0
        writer.tool_call("id1", "bash", {}, "bash", {}, [])
        assert writer.total_tool_calls == 1
        writer.tool_call("id2", "grep", {}, "grep", {}, [])
        assert writer.total_tool_calls == 2

    def test_session_start(self, audit_file):
        """Verify session_start writes system prompt and tool schema."""
        writer = AuditWriter(audit_file)
        writer.session_start(
            "test-model", 5, "/tmp",
            "You are an agent.",
            [{"name": "bash"}],
        )
        writer.flush()
        content = audit_file.read_text()
        assert "SESSION_START" in content
        assert "system_prompt:" in content
        assert "You are an agent." in content
        assert "tool_schema:" in content


class TestAuditWriterIntegration:
    """Integration tests for AuditWriter."""

    def test_turn_cycle(self, audit_file):
        """Simulate a full turn: user → tool_call → tool_result → assistant → flush.

        Verify all records present and in correct order.
        """
        writer = AuditWriter(audit_file)
        writer.user("read file.txt")
        writer.tool_call(
            "c1", "file_read", {"path": "file.txt"},
            "file_read", {"path": "file.txt"}, [],
        )
        writer.tool_result("c1", "ok", 50.0, "file contents here", 20)
        writer.assistant("The file contains: file contents here")
        writer.flush()

        content = audit_file.read_text()
        # Verify all records present
        assert "USER" in content
        assert "TOOL_CALL" in content
        assert "TOOL_RESULT" in content
        assert "ASSISTANT" in content
        # Verify ordering
        assert content.index("USER") < content.index("TOOL_CALL")
        assert content.index("TOOL_CALL") < content.index("TOOL_RESULT")
        assert content.index("TOOL_RESULT") < content.index("ASSISTANT")


class TestAuditWriterRegression:
    """Regression tests for thread removal."""

    def test_no_threads_created(self, audit_file):
        """Verify AuditWriter does not spawn any threads."""
        before = threading.active_count()
        writer = AuditWriter(audit_file)
        writer.user("test")
        writer.flush()
        after = threading.active_count()
        assert before == after, (
            f"AuditWriter should not spawn threads "
            f"(before={before}, after={after})"
        )

    def test_close_is_flush(self, audit_file):
        """Verify close() flushes data (backward compatibility)."""
        writer = AuditWriter(audit_file)
        writer.user("before close")
        writer.close()
        assert audit_file.exists()
        assert "before close" in audit_file.read_text()
