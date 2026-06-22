"""Tests for TauContext.attempt_recovery() context recovery mechanism."""
import pytest
from agent_context import TauContext


class TestAttemptRecoveryMalformedMessages:
    def test_removes_non_dict_entries(self):
        ctx = TauContext()
        ctx._messages = [
            {"role": "system", "content": "System"},
            "not a dict",
            {"role": "user", "content": "Hello"},
        ]
        recovered, fixes = ctx.attempt_recovery()
        assert any("Removed 1 malformed" in f for f in fixes)
        assert all(isinstance(m, dict) for m in ctx._messages)
        # After removing malformed entry, context is [system, user] which is valid
        assert recovered

    def test_no_malformed_no_fix(self):
        ctx = TauContext()
        ctx._messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Hello"},
        ]
        recovered, fixes = ctx.attempt_recovery()
        assert not recovered
        assert fixes == []


class TestAttemptRecoveryMissingSystem:
    def test_adds_missing_system_message(self):
        ctx = TauContext()
        ctx._messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        recovered, fixes = ctx.attempt_recovery()
        assert any("Added missing system message" in f for f in fixes)
        assert ctx._messages[0].get("role") == "system"


class TestAttemptRecoveryConsecutiveRoles:
    def test_fixes_consecutive_user_messages(self):
        ctx = TauContext()
        ctx._messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "A"},
            {"role": "user", "content": "B"},
        ]
        recovered, fixes = ctx.attempt_recovery()
        assert any("consecutive user" in f.lower() for f in fixes)

    def test_fixes_consecutive_assistant_messages(self):
        ctx = TauContext()
        ctx._messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A1"},
            {"role": "assistant", "content": "A2"},
        ]
        recovered, fixes = ctx.attempt_recovery()
        assert any("consecutive assistant" in f.lower() for f in fixes)

    def test_system_then_assistant_bridge(self):
        ctx = TauContext()
        ctx._messages = [
            {"role": "system", "content": "System"},
            {"role": "assistant", "content": "Hi"},
        ]
        recovered, fixes = ctx.attempt_recovery()
        assert any("bridge after system" in f.lower() for f in fixes)


class TestAttemptRecoveryUnresolvedToolCalls:
    def test_adds_placeholder_for_unresolved_tools(self):
        ctx = TauContext()
        ctx._messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": None,
             "tool_calls": [{"id": "call_1", "function": {"name": "bash", "arguments": "{}"}}]},
        ]
        recovered, fixes = ctx.attempt_recovery()
        assert any("placeholder" in f.lower() for f in fixes)
        tool_msgs = [m for m in ctx._messages if m.get("role") == "tool"]
        assert len(tool_msgs) >= 1


class TestAttemptRecoverySnapshotRollback:
    def test_rollback_when_recovery_makes_worse(self):
        """If recovery would increase errors, original state is restored."""
        ctx = TauContext()
        # Valid context — recovery has nothing to fix
        ctx._messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Hello"},
        ]
        original = list(ctx._messages)
        recovered, fixes = ctx.attempt_recovery()
        assert not recovered
        assert fixes == []
        assert ctx._messages == original

    def test_snapshot_restored_on_exception(self):
        """Exception during recovery restores original state."""
        ctx = TauContext()
        ctx._messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Hello"},
        ]
        original = list(ctx._messages)
        # Force exception by breaking get_pending_tool_ids
        ctx.get_pending_tool_ids = lambda: 1 / 0  # noqa
        recovered, fixes = ctx.attempt_recovery()
        assert not recovered
        assert any("Recovery failed" in f for f in fixes)
        assert ctx._messages == original


class TestAttemptRecoveryToolFollowedByUser:
    def test_fixes_tool_then_user(self):
        ctx = TauContext()
        ctx._messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": None,
             "tool_calls": [{"id": "call_1", "function": {"name": "bash", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "call_1", "name": "bash", "content": "ok"},
            {"role": "user", "content": "Next"},
        ]
        recovered, fixes = ctx.attempt_recovery()
        assert any("tool and user" in f.lower() for f in fixes)


class TestAttemptRecoveryEdgeCases:
    def test_empty_context(self):
        ctx = TauContext()
        ctx._messages = []
        recovered, fixes = ctx.attempt_recovery()
        assert not recovered
        assert fixes == []

    def test_already_valid_context(self):
        ctx = TauContext()
        ctx._messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        recovered, fixes = ctx.attempt_recovery()
        assert not recovered
        assert fixes == []

    def test_multiple_fixes_combined(self):
        """Context with multiple issues gets multiple fixes."""
        ctx = TauContext()
        ctx._messages = [
            "bad",  # malformed
            {"role": "user", "content": "A"},  # no system
            {"role": "user", "content": "B"},  # consecutive
        ]
        recovered, fixes = ctx.attempt_recovery()
        assert len(fixes) >= 2  # At least: malformed removal + system + consecutive
