"""Tests for recover_from_invalid_end_of_turn synthetic bridge behavior.

Verifies that recover_from_invalid_end_of_turn uses synthetic bridges
instead of direct _messages access, maintaining consistent context alternation.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_context import TauContext
from agent_message_utils import _SYNTHETIC_PREFIX, is_synthetic_message
from agent_loop_detect import LoopDetector
from agent_reflection import ReflectionScheduler, ReflectionConfig
from agent_loop_escalation import LoopEscalationManager


class TestRecoverFromInvalidEndOfTurn:
    """Test that recover_from_invalid_end_of_turn uses synthetic bridges."""

    def _make_manager(self):
        """Create a LoopEscalationManager with a valid context."""
        ctx = TauContext()
        ctx.set_system("You are a helpful assistant.")
        ctx.append_user("What is 2+2?")
        ctx.append_assistant("4")
        
        detector = LoopDetector()
        scheduler = ReflectionScheduler(ReflectionConfig())
        agent = MagicMock()
        
        return LoopEscalationManager(detector, scheduler, ctx, agent), ctx

    def test_uses_synthetic_bridge_not_direct_merge(self):
        """recover_from_invalid_end_of_turn uses append_synthetic_user, not _messages access."""
        manager, ctx = self._make_manager()
        
        # Call recovery
        manager.recover_from_invalid_end_of_turn("Incomplete response...", None)
        
        # Verify a synthetic user message was appended
        msgs = ctx.get_messages()
        synthetic_msgs = [m for m in msgs if is_synthetic_message(m)]
        assert len(synthetic_msgs) == 1, f"Expected 1 synthetic message, got {len(synthetic_msgs)}"
        
        # Verify it's a user role
        assert synthetic_msgs[0]["role"] == "user"
        
        # Verify it has the recovery category
        assert "recovery" in synthetic_msgs[0]["content"].lower() or _SYNTHETIC_PREFIX in synthetic_msgs[0]["content"]

    def test_synthetic_bridge_has_correct_prefix(self):
        """The synthetic bridge is properly marked with _SYNTHETIC_PREFIX."""
        manager, ctx = self._make_manager()
        
        manager.recover_from_invalid_end_of_turn("Truncated response", None)
        
        msgs = ctx.get_messages()
        synthetic_msgs = [m for m in msgs if is_synthetic_message(m)]
        
        assert len(synthetic_msgs) == 1
        assert _SYNTHETIC_PREFIX in synthetic_msgs[0]["content"]

    def test_context_remains_valid_after_recovery(self):
        """The context has no validation errors after recovery."""
        manager, ctx = self._make_manager()
        
        manager.recover_from_invalid_end_of_turn("Incomplete...", None)
        
        errors = ctx.validate()
        # Should have no consecutive-role errors
        consecutive_errors = [e for e in errors if "consecutive" in e.lower()]
        assert consecutive_errors == [], f"Expected no consecutive errors, got: {consecutive_errors}"

    def test_recovery_content_contains_expected_keywords(self):
        """The recovery message contains expected keywords."""
        manager, ctx = self._make_manager()
        
        manager.recover_from_invalid_end_of_turn("Incomplete response", None)
        
        msgs = ctx.get_messages()
        synthetic_msgs = [m for m in msgs if is_synthetic_message(m)]
        
        assert len(synthetic_msgs) == 1
        content = synthetic_msgs[0]["content"].lower()
        
        # Check for expected keywords
        assert "structurally incomplete" in content or "incomplete" in content
        assert "end_turn" in content

    def test_recovery_preserves_last_real_prompt(self):
        """The recovery message includes the last real user prompt."""
        manager, ctx = self._make_manager()
        
        # Add a user message to be included in recovery
        ctx.append_user("Please explain quantum computing.")
        ctx.append_assistant("Quantum computing uses qubits...")
        
        manager.recover_from_invalid_end_of_turn("Incomplete explanation", None)
        
        msgs = ctx.get_messages()
        synthetic_msgs = [m for m in msgs if is_synthetic_message(m)]
        
        assert len(synthetic_msgs) == 1
        content = synthetic_msgs[0]["content"]
        
        # Should include the last real user prompt
        assert "quantum computing" in content.lower()

    def test_no_private_messages_access(self):
        """Verify that recover_from_invalid_end_of_turn doesn't access _messages directly."""
        # This is a static analysis check - we verify by inspecting the source
        import inspect
        from agent_loop_escalation import LoopEscalationManager
        
        source = inspect.getsource(LoopEscalationManager.recover_from_invalid_end_of_turn)
        
        # Should NOT contain direct _messages access (but get_messages() is OK)
        # Check for patterns like self._context._messages or _messages[
        assert "._messages" not in source, "Should not access _messages attribute directly"
        assert "append_synthetic_user" in source, "Should use append_synthetic_user"
