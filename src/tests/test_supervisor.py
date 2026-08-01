"""Tests for the Supervisor class and server-side supervision handling.

Tests the Supervisor class that connects to a child agent's A2A socket
and sends control commands (inject, terminate, redirect, status).
Also tests the audit tailing and loop detection features.
"""

import json
import os
import socket
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_a2a import Supervisor


class TestSupervisorInit:
    """Test Supervisor initialization."""

    def test_init_attributes(self):
        """Supervisor stores all required attributes."""
        sup = Supervisor(
            task="test task",
            child_pid=12345,
            sock_path="/tmp/test.sock",
            audit_file=Path("/tmp/test.audit"),
        )
        assert sup.task == "test task"
        assert sup.child_pid == 12345
        assert sup.sock_path == "/tmp/test.sock"
        assert sup.audit_file == Path("/tmp/test.audit")
        assert sup._sock is None
        assert sup._cmd_id == 0
        assert sup._last_audit_pos == 0


class TestSupervisorAuditTailing:
    """Test audit log tailing functionality."""

    def test_get_new_audit_lines_empty(self, tmp_path):
        """Returns empty string when audit file doesn't exist."""
        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=tmp_path / "nonexistent.audit",
        )
        assert sup.get_new_audit_lines() == ""

    def test_get_new_audit_lines_new_content(self, tmp_path):
        """Returns new content written to audit file."""
        audit_file = tmp_path / "audit.log"
        audit_file.write_text("initial content\n")

        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=audit_file,
        )
        # First read gets initial content
        lines = sup.get_new_audit_lines()
        assert "initial content" in lines

        # Second read gets nothing (no new content)
        lines = sup.get_new_audit_lines()
        assert lines == ""

        # Append new content (write_text overwrites, so use append)
        with open(audit_file, "a") as f:
            f.write("new content\n")
        lines = sup.get_new_audit_lines()
        assert "new content" in lines

    def test_get_new_audit_lines_incremental(self, tmp_path):
        """Only returns content since last read."""
        audit_file = tmp_path / "audit.log"
        audit_file.write_text("line1\nline2\n")

        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=audit_file,
        )
        lines = sup.get_new_audit_lines()
        assert "line1" in lines
        assert "line2" in lines

        # No new content
        assert sup.get_new_audit_lines() == ""


class TestSupervisorLoopDetection:
    """Test loop detection in audit log."""

    def _write_audit_with_tool_calls(self, tmp_path, calls: list[dict]) -> Path:
        """Write audit file with tool call records."""
        audit_file = tmp_path / "audit.log"
        lines = []
        for call in calls:
            lines.append(json.dumps({"tool_call": call}))
        audit_file.write_text("\n".join(lines) + "\n")
        return audit_file

    def test_detect_loop_repeated_calls(self, tmp_path):
        """Detects repeated tool+args pattern."""
        calls = [
            {"name": "bash", "args": '{"cmd": "ls"}'}
            for _ in range(5)
        ]
        audit_file = self._write_audit_with_tool_calls(tmp_path, calls)

        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=audit_file,
        )
        assert sup.detect_loop(window=3) is True

    def test_detect_loop_no_repetition(self, tmp_path):
        """Returns False when no repeated pattern."""
        calls = [
            {"name": "bash", "args": '{"cmd": "ls"}'},
            {"name": "file_read", "args": '{"path": "/tmp"}'},
            {"name": "bash", "args": '{"cmd": "pwd"}'},
            {"name": "file_write", "args": '{"path": "/tmp/out"}'},
            {"name": "bash", "args": '{"cmd": "cat"}'},
        ]
        audit_file = self._write_audit_with_tool_calls(tmp_path, calls)

        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=audit_file,
        )
        assert sup.detect_loop(window=3) is False

    def test_detect_loop_insufficient_data(self, tmp_path):
        """Returns None when not enough data."""
        calls = [
            {"name": "bash", "args": '{"cmd": "ls"}'},
            {"name": "bash", "args": '{"cmd": "ls"}'},
        ]
        audit_file = self._write_audit_with_tool_calls(tmp_path, calls)

        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=audit_file,
        )
        assert sup.detect_loop(window=5) is None

    def test_detect_loop_no_audit_data(self, tmp_path):
        """Returns None when no audit data available."""
        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=tmp_path / "nonexistent.audit",
        )
        assert sup.detect_loop() is None

    def test_detect_loop_mixed_format(self, tmp_path):
        """Handles both tool_call and tool_calls formats."""
        audit_file = tmp_path / "audit.log"
        # Mix of single tool_call and tool_calls array
        lines = [
            json.dumps({"tool_call": {"name": "bash", "args": '{"cmd": "ls"}'}}),
            json.dumps({"tool_calls": [{"name": "bash", "args": '{"cmd": "ls"}'}]}),
            json.dumps({"tool_call": {"name": "bash", "args": '{"cmd": "ls"}'}}),
        ]
        audit_file.write_text("\n".join(lines) + "\n")

        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=audit_file,
        )
        assert sup.detect_loop(window=3) is True


class TestSupervisorClose:
    """Test Supervisor close functionality."""

    def test_close_without_connect(self):
        """Close works without prior connection (no-op)."""
        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=Path("/tmp/test.audit"),
        )
        sup.close()  # Should not raise
        assert sup._sock is None

    def test_close_sends_close_command(self):
        """Close sends close command before closing socket."""
        mock_sock = MagicMock()
        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=Path("/tmp/test.audit"),
        )
        sup._sock = mock_sock

        sup.close()

        # Verify close command was sent
        mock_sock.send.assert_called_once()
        sent_data = json.loads(mock_sock.send.call_args[0][0])
        assert sent_data == {"type": "close"}
        mock_sock.close.assert_called_once()


class TestSupervisorCommandBuilding:
    """Test command building for supervisor methods."""

    def test_inject_command_format(self):
        """Inject builds correct command format."""
        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=Path("/tmp/test.audit"),
        )
        sup._cmd_id = 0
        # Verify _cmd_id increments
        sup._cmd_id += 1
        cmd = {"type": "inject", "role": "user", "content": "hello", "id": f"cmd-{sup._cmd_id}"}
        assert cmd["type"] == "inject"
        assert cmd["role"] == "user"
        assert cmd["content"] == "hello"
        assert cmd["id"] == "cmd-1"

    def test_terminate_command_format(self):
        """Terminate builds correct command format."""
        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=Path("/tmp/test.audit"),
        )
        sup._cmd_id = 0
        sup._cmd_id += 1
        cmd = {"type": "terminate", "graceful": True, "id": f"cmd-{sup._cmd_id}"}
        assert cmd["type"] == "terminate"
        assert cmd["graceful"] is True
        assert cmd["id"] == "cmd-1"

    def test_redirect_command_format(self):
        """Redirect builds correct command format."""
        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=Path("/tmp/test.audit"),
        )
        sup._cmd_id = 0
        sup._cmd_id += 1
        cmd = {"type": "redirect", "task": "new task", "id": f"cmd-{sup._cmd_id}"}
        assert cmd["type"] == "redirect"
        assert cmd["task"] == "new task"
        assert cmd["id"] == "cmd-1"


class TestSupervisorCmdIdIncrement:
    """Test that _cmd_id increments correctly."""

    def test_cmd_id_increments_on_inject(self):
        """_cmd_id increments when inject is called."""
        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=Path("/tmp/test.audit"),
        )
        assert sup._cmd_id == 0
        sup._cmd_id += 1
        assert sup._cmd_id == 1
        sup._cmd_id += 1
        assert sup._cmd_id == 2

    def test_cmd_id_increments_on_terminate(self):
        """_cmd_id increments when terminate is called."""
        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=Path("/tmp/test.audit"),
        )
        assert sup._cmd_id == 0
        sup._cmd_id += 1
        assert sup._cmd_id == 1

    def test_cmd_id_increments_on_redirect(self):
        """_cmd_id increments when redirect is called."""
        sup = Supervisor(
            task="test", child_pid=1, sock_path="/tmp/test.sock",
            audit_file=Path("/tmp/test.audit"),
        )
        assert sup._cmd_id == 0
        sup._cmd_id += 1
        assert sup._cmd_id == 1
