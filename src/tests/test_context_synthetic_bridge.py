"""Tests for synthetic bridge insertion in append_assistant().

Verifies that invalid message sequences are automatically corrected by
inserting synthetic user messages, maintaining valid OpenAI alternation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_context import TauContext
from agent_message_utils import _SYNTHETIC_PREFIX, is_synthetic_message


class TestSyntheticBridgeInsertion:
    """Test that append_assistant() inserts synthetic bridges for invalid sequences."""

    def _make_valid_context(self):
        """Create a minimal valid context: system → user."""
        ctx = TauContext()
        ctx.set_system("You are a helpful assistant.")
        ctx.append_user("Hello")
        return ctx

    def test_consecutive_assistant_inserts_bridge(self):
        """Consecutive assistant messages get a synthetic user bridge."""
        ctx = self._make_valid_context()
        ctx.append_assistant("First response.")
        # Last role is now "assistant" — next append should insert bridge
        ctx.append_assistant("Second response.")

        # Should have: system, user, assistant, [synthetic user], assistant
        msgs = ctx.get_messages()
        assert len(msgs) == 5, f"Expected 5 messages, got {len(msgs)}"

        # Verify roles
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert msgs[2]["role"] == "assistant"
        assert msgs[3]["role"] == "user"  # synthetic bridge
        assert msgs[4]["role"] == "assistant"

        # Verify bridge is synthetic
        assert is_synthetic_message(msgs[3]), "Bridge should be synthetic"
        assert _SYNTHETIC_PREFIX in msgs[3]["content"]

    def test_consecutive_assistant_no_validation_errors(self):
        """After bridge insertion, validate() should return no errors."""
        ctx = self._make_valid_context()
        ctx.append_assistant("First response.")
        ctx.append_assistant("Second response.")

        errors = ctx.validate()
        assert errors == [], f"Expected no validation errors, got: {errors}"

    def test_system_to_assistant_with_multiple_messages_inserts_bridge(self):
        """System → assistant (with >1 message) gets a synthetic bridge."""
        ctx = TauContext()
        ctx.set_system("System prompt.")
        ctx.append_user("User message.")
        # Now manually set last message to system (simulating edge case)
        ctx._messages[-1] = {"role": "system", "content": "Another system msg."}

        # Append assistant — should insert bridge since last is system and len > 1
        ctx.append_assistant("Assistant response.")

        msgs = ctx.get_messages()
        # Should have: system, user, system, [synthetic user], assistant
        assert any(is_synthetic_message(m) for m in msgs), "Should have synthetic bridge"

    def test_invalid_predecessor_inserts_bridge(self):
        """Invalid predecessor role gets a synthetic bridge."""
        ctx = self._make_valid_context()
        ctx.append_assistant("Response with tool calls.", tool_calls=[
            {"id": "call_1", "function": {"name": "test", "arguments": "{}"}}
        ])
        ctx.append_tool("Tool result", "call_1")
        # Last role is "tool" — valid predecessor, no bridge needed
        ctx.append_assistant("After tool result.")

        # This should NOT insert a bridge (tool → assistant is valid)
        msgs = ctx.get_messages()
        # Count non-synthetic messages
        real_msgs = [m for m in msgs if not is_synthetic_message(m)]
        # system, user, assistant, tool, assistant = 5 real messages
        assert len(real_msgs) == 5, f"Expected 5 real messages, got {len(real_msgs)}"

    def test_multiple_consecutive_assistants(self):
        """Multiple consecutive assistant messages each get their own bridge."""
        ctx = self._make_valid_context()
        ctx.append_assistant("First.")
        ctx.append_assistant("Second.")
        ctx.append_assistant("Third.")

        msgs = ctx.get_messages()
        # system, user, assistant, bridge, assistant, bridge, assistant
        assert len(msgs) == 7, f"Expected 7 messages, got {len(msgs)}"

        # Verify all bridges are synthetic
        bridges = [m for m in msgs if is_synthetic_message(m)]
        assert len(bridges) == 2, f"Expected 2 bridges, got {len(bridges)}"

    def test_bridge_excluded_from_validation(self):
        """Synthetic bridges should not trigger consecutive-role errors."""
        ctx = self._make_valid_context()
        ctx.append_assistant("First.")
        ctx.append_assistant("Second.")
        ctx.append_assistant("Third.")

        errors = ctx.validate()
        # Should have no errors — bridges are excluded from consecutive-role check
        consecutive_errors = [e for e in errors if "consecutive" in e.lower()]
        assert consecutive_errors == [], f"Bridge should prevent consecutive errors: {consecutive_errors}"

    def test_bridge_preserves_assistant_content(self):
        """Both assistant messages should be preserved with their content."""
        ctx = self._make_valid_context()
        ctx.append_assistant("Response A")
        ctx.append_assistant("Response B")

        msgs = ctx.get_messages()
        assistant_msgs = [m for m in msgs if m["role"] == "assistant" and not is_synthetic_message(m)]
        assert len(assistant_msgs) == 2
        assert assistant_msgs[0]["content"] == "Response A"
        assert assistant_msgs[1]["content"] == "Response B"

    def test_valid_sequence_no_bridge(self):
        """Valid user → assistant sequence should NOT insert a bridge."""
        ctx = self._make_valid_context()
        ctx.append_assistant("Response.")

        msgs = ctx.get_messages()
        # system, user, assistant = 3 messages, no bridge
        assert len(msgs) == 3, f"Expected 3 messages, got {len(msgs)}"
        assert not any(is_synthetic_message(m) for m in msgs), "No bridge for valid sequence"

    def test_tool_to_assistant_no_bridge(self):
        """tool → assistant is valid, should NOT insert a bridge."""
        ctx = self._make_valid_context()
        ctx.append_assistant("Response with tool call.", tool_calls=[
            {"id": "call_1", "function": {"name": "test", "arguments": "{}"}}
        ])
        ctx.append_tool("Result", "call_1")
        ctx.append_assistant("After tool.")

        msgs = ctx.get_messages()
        # system, user, assistant, tool, assistant = 5 messages
        assert len(msgs) == 5, f"Expected 5 messages, got {len(msgs)}"
        assert not any(is_synthetic_message(m) for m in msgs), "No bridge for valid tool→assistant"


class TestSyntheticBridgeCleanup:
    """Test that synthetic bridges are cleaned up properly."""

    def test_cleanup_removes_bridges(self):
        """cleanup_synthetic() should remove all synthetic messages."""
        ctx = TauContext()
        ctx.set_system("System.")
        ctx.append_user("User.")
        ctx.append_assistant("First.")
        ctx.append_assistant("Second.")  # Inserts bridge

        assert any(is_synthetic_message(m) for m in ctx.get_messages())

        ctx.cleanup_synthetic()

        # After cleanup, no synthetic messages should remain
        assert not any(is_synthetic_message(m) for m in ctx.get_messages())

    def test_cleanup_preserves_real_messages(self):
        """cleanup_synthetic() removes synthetic bridges WITHOUT merging (explicit merge design).

        Under explicit merge, cleanup_synthetic() removes bridges only.
        The caller must explicitly call merge_consecutive_assistants() to consolidate.
        See designs/DECISIONS.md §18.7.
        """
        ctx = TauContext()
        ctx.set_system("System.")
        ctx.append_user("User.")
        ctx.append_assistant("First.")
        ctx.append_assistant("Second.")

        ctx.cleanup_synthetic()

        msgs = ctx.get_messages()
        # system, user, assistant, assistant (synthetic removed, NO merge)
        assert len(msgs) == 4
        assert msgs[0] == {"role": "system", "content": "System."}
        assert msgs[1] == {"role": "user", "content": "User."}
        assert msgs[2]["role"] == "assistant"
        assert msgs[2]["content"] == "First."
        assert msgs[3]["role"] == "assistant"
        assert msgs[3]["content"] == "Second."

    def test_close_turn_cleans_and_merges(self):
        """close_turn() cleans up synthetic bridges AND merges consecutive messages (explicit merge).

        Under explicit merge design, close_turn() calls cleanup_synthetic() to remove
        bridges, then merge_consecutive_assistants() to consolidate consecutive
        assistant messages.
        See designs/DECISIONS.md §18.7.
        """
        ctx = TauContext()
        ctx.set_system("System.")
        ctx.append_user("User.")
        ctx.append_assistant("First.")
        ctx.append_assistant("Second.")

        assert any(is_synthetic_message(m) for m in ctx.get_messages())

        ctx.close_turn("turn complete")

        # After close_turn, bridges should be cleaned AND consecutive messages merged
        assert not any(is_synthetic_message(m) for m in ctx.get_messages())
        msgs = ctx.get_messages()
        # system, user, assistant (merged: "First.\nSecond.\n...")
        assistant_msgs = [m for m in msgs if m["role"] == "assistant"]
        assert len(assistant_msgs) == 1, f"Expected 1 merged assistant, got {len(assistant_msgs)}"
        assert "First." in assistant_msgs[0]["content"]
        assert "Second." in assistant_msgs[0]["content"]
