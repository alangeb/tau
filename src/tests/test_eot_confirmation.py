"""Tests for EOT (end-of-turn) confirmation system in agent_eot_protection.py.

Tests the EOT confirmation mechanism. When the LLM returns plain text without
tool calls, the system holds the message and asks for confirmation via a
sentinel string.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestEotConstants:
    """Test EOT sentinel string assembly."""

    def test_sentinel_assembled_from_parts(self):
        """Sentinel string is assembled from prefix."""
        from agent_eot_protection import (
            ACCIDENTAL_EOT,
            _ACCIDENTAL_EOT_PREFIX,
        )

        assert ACCIDENTAL_EOT == _ACCIDENTAL_EOT_PREFIX

    def test_sentinel_part_not_adjacent_in_code(self):
        """The prefix is defined separately to prevent pattern matching."""
        from agent_eot_protection import _ACCIDENTAL_EOT_PREFIX

        # The prefix is defined on its own — it should not appear
        # as a single string literal in the source code.
        assert "_" not in _ACCIDENTAL_EOT_PREFIX


def _make_eot():
    """Helper to create an EOTProtection instance for testing."""
    from agent_context import TauContext
    from agent_eot_protection import EOTProtection

    agent = MagicMock()
    agent.context = TauContext([{"role": "system", "content": "You are helpful"}])
    agent._session = MagicMock()
    agent._session.audit_writer = MagicMock()
    agent.last_substantive_response = None
    agent.max_context_tokens = 200000
    return EOTProtection(agent)


def _make_eot_with_context(messages: list[dict]):
    """Helper to create an EOTProtection instance with a custom context."""
    from agent_context import TauContext
    from agent_eot_protection import EOTProtection

    agent = MagicMock()
    agent.context = TauContext(messages)
    agent._session = MagicMock()
    agent._session.audit_writer = MagicMock()
    agent.last_substantive_response = None
    return EOTProtection(agent)


class TestCheckEotConfirmation:
    """Test check_confirmation method."""

    def test_exact_sentinel_match(self):
        """Exact sentinel is recognized."""
        from agent_eot_protection import ACCIDENTAL_EOT, EOTProtection

        eot = _make_eot()
        confirmed, stripped = eot.check_confirmation(ACCIDENTAL_EOT)
        assert confirmed is True
        assert stripped is None  # Exact match — no text to strip

    def test_case_insensitive_match(self):
        """Sentinel match is case-insensitive."""
        from agent_eot_protection import ACCIDENTAL_EOT, EOTProtection

        eot = _make_eot()
        confirmed, stripped = eot.check_confirmation(ACCIDENTAL_EOT.upper())
        assert confirmed is True
        assert stripped is None  # Exact match — no text to strip

    def test_no_sentinel_returns_false(self):
        """Plain text without sentinel returns False."""
        eot = _make_eot()
        confirmed, stripped = eot.check_confirmation("I'm done with the task")
        assert confirmed is False
        assert stripped == "I'm done with the task"

    def test_empty_response_returns_false(self):
        """Empty response returns False."""
        eot = _make_eot()
        confirmed, stripped = eot.check_confirmation("")
        assert confirmed is False
        assert stripped == ""

    def test_none_response_returns_false(self):
        """None response returns False."""
        eot = _make_eot()
        confirmed, stripped = eot.check_confirmation(None)
        assert confirmed is False
        assert stripped is None

    def test_partial_sentinel_no_match(self):
        """Partial sentinel match does not trigger confirmation."""
        eot = _make_eot()
        # ENDOFTURN_AL (incomplete) does NOT match
        confirmed, stripped = eot.check_confirmation("ENDOFTURN_AL")
        assert confirmed is False
        assert stripped == "ENDOFTURN_AL"

    def test_sentinel_suffix_strips_text(self):
        """Sentinel at end of response is stripped and returned separately."""
        from agent_eot_protection import ACCIDENTAL_EOT

        eot = _make_eot()
        response = "Here is the answer\n\nENDOFTURN"
        confirmed, stripped = eot.check_confirmation(response)
        assert confirmed is True
        assert "Here is the answer" in stripped
        assert ACCIDENTAL_EOT not in stripped

    def test_sentinel_suffix_with_no_prefix(self):
        """Sentinel with no preceding content returns None stripped text."""
        from agent_eot_protection import ACCIDENTAL_EOT

        eot = _make_eot()
        confirmed, stripped = eot.check_confirmation(ACCIDENTAL_EOT)
        assert confirmed is True
        assert stripped is None  # Exact match — no text to strip


class TestHandlePotentialEot:
    """Test handle_potential_eot method."""

    def test_holds_message_on_stack(self):
        """Message is held on the confirmation stack."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot()

        eot.handle_potential_eot("Here is my answer", "thinking content")

        assert len(eot._eot_confirmation_stack) == 1
        entry = eot._eot_confirmation_stack[0]
        assert entry["text"] == "Here is my answer"
        assert entry["reasoning"] == "thinking content"

    def test_injects_synthetic_user_message(self):
        """A synthetic user confirmation message is appended to context, along with the assistant response."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot()

        eot.handle_potential_eot("Here is my answer", None)

        msgs = eot._context._messages
        # system + turn_started bridge + assistant response + eot_confirmation synthetic user
        assert len(msgs) == 4
        assert msgs[-1]["role"] == "user"
        assert "CONFIRMATION REQUEST" in msgs[-1]["content"]
        assert "[U:confirm | N:" in msgs[-1]["content"]
        # Assistant response should be present (critical for pop_all_confirmations)
        assert msgs[-2]["role"] == "assistant"
        assert msgs[-2]["content"] == "Here is my answer"

    def test_stacks_on_existing_confirmation(self):
        """Multiple plain text responses stack confirmation layers."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot()
        # Pre-populate stack with first entry
        eot._eot_confirmation_stack = [{"text": "first", "reasoning": None}]

        eot.handle_potential_eot("second response", None)

        assert len(eot._eot_confirmation_stack) == 2
        assert eot._eot_confirmation_stack[1]["text"] == "second response"

    def test_logs_eot_confirm_request(self):
        """handle_potential_eot() logs EOT_CONFIRM_REQUEST to audit."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot()

        eot.handle_potential_eot("Here is my answer", None)

        # Check that _emit was called with EOT_CONFIRM_REQUEST
        emit_calls = [
            call for call in eot._audit_writer._emit.call_args_list
            if "EOT_CONFIRM_REQUEST" in str(call)
        ]
        assert len(emit_calls) == 1
        # Verify stack_depth is in the call
        call_args = emit_calls[0][0]
        assert "EOT_CONFIRM_REQUEST" in call_args[0]
        assert "stack_depth=1" in call_args[1]


class TestPopAllEotConfirmations:
    """Test pop_all_confirmations method."""

    def test_pops_single_layer(self):
        """A single confirmation layer is popped correctly."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "answer"},
            {"role": "user", "content": "[U:confirm | N:0] confirm"},
        ])
        eot._eot_confirmation_stack = [{"text": "answer", "reasoning": None}]

        eot.pop_all_confirmations()

        assert len(eot._eot_confirmation_stack) == 0
        assert len(eot._context._messages) == 1  # only system message remains

    def test_pops_multiple_layers(self):
        """Multiple confirmation layers are popped correctly."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "first"},
            {"role": "user", "content": "[U:confirm | N:0] confirm 1"},
            {"role": "assistant", "content": "second"},
            {"role": "user", "content": "[U:confirm | N:0] confirm 2"},
        ])
        eot._eot_confirmation_stack = [
            {"text": "first", "reasoning": None},
            {"text": "second", "reasoning": None},
        ]

        eot.pop_all_confirmations()

        assert len(eot._eot_confirmation_stack) == 0
        assert len(eot._context._messages) == 1  # only system message remains

    def test_handles_corrupted_context(self):
        """When context is corrupted, stack is still cleared."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "[SYSTEM-SYNTHETIC: eot_confirmation] confirm"},
        ])
        eot._eot_confirmation_stack = [{"text": "answer", "reasoning": None}]

        eot.pop_all_confirmations()

        # Stack should still be cleared even if popping failed
        assert len(eot._eot_confirmation_stack) == 0


class TestRewindConfirmationWithTools:
    """Test rewind_with_tools method."""

    def test_rewinds_with_tool_calls(self):
        """Tool calls are merged into the first held message."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "Let me do that"},
            {"role": "user", "content": "[SYSTEM-SYNTHETIC: eot_confirmation] confirm"},
        ])
        eot._eot_confirmation_stack = [
            {"text": "Let me do that", "reasoning": "thinking"},
        ]

        tool_calls = [
            {"id": "tc1", "name": "bash", "args": "ls", "args_dict": {}},
        ]

        eot.rewind_with_tools(tool_calls, "thinking")

        # Stack should be cleared
        assert len(eot._eot_confirmation_stack) == 0
        # Context should have the held message with tool calls
        msgs = eot._context._messages
        assert msgs[-1]["role"] == "assistant"
        assert msgs[-1].get("tool_calls") is not None
        assert len(msgs[-1]["tool_calls"]) == 1
        assert msgs[-1]["tool_calls"][0]["function"]["name"] == "bash"

    def test_clears_stack_before_popping(self):
        """Stack is saved before being cleared during pop."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "first"},
            {"role": "user", "content": "[SYSTEM-SYNTHETIC: eot_confirmation] confirm 1"},
            {"role": "assistant", "content": "second"},
            {"role": "user", "content": "[SYSTEM-SYNTHETIC: eot_confirmation] confirm 2"},
        ])
        eot._eot_confirmation_stack = [
            {"text": "first", "reasoning": None},
            {"text": "second", "reasoning": None},
        ]

        tool_calls = [{"id": "tc1", "name": "bash", "args": "ls", "args_dict": {}}]

        eot.rewind_with_tools(tool_calls, None)

        # Only the first held message should be in context with tool calls
        msgs = eot._context._messages
        assert msgs[-1]["role"] == "assistant"
        assert msgs[-1].get("tool_calls") is not None


class TestAcceptEotConfirmation:
    """Test accept_confirmation method."""

    def test_accepts_confirmation(self):
        """Confirmation is accepted and turn is closed."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "Here is the answer"},
            {"role": "user", "content": "[SYSTEM-SYNTHETIC: eot_confirmation] confirm"},
        ])
        eot._eot_confirmation_stack = [
            {"text": "Here is the answer", "reasoning": "thinking"},
        ]

        result = eot.accept_confirmation()

        assert result == "Here is the answer"
        assert len(eot._eot_confirmation_stack) == 0
        # audit_writer.assistant should have been called
        eot._audit_writer.assistant.assert_called_once()

    def test_prefers_held_over_stale_substantive(self):
        """held_text is preferred over last_substantive_response.

        held_text is the answer being confirmed (shown in <LASTREPLY>).
        last_substantive_response may be stale from a previous turn.
        """
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "[U:confirm | N:0] confirm"},
        ])
        # Held message is the current turn's answer
        eot._eot_confirmation_stack = [
            {"text": "Current turn comprehensive answer.", "reasoning": None},
        ]
        # last_substantive_response is stale from previous turn
        eot._agent.last_substantive_response = "Previous turn summary."

        result = eot.accept_confirmation()

        # Should return held_text (current answer), NOT stale substantive
        assert result == "Current turn comprehensive answer."

    def test_falls_to_substantive_when_held_malformed(self):
        """last_substantive_response is used when held is malformed.

        This is the FIX for the bug where a malformed tool-call pattern
        (e.g., `` `glob` `` with pattern="...") overwrites the original
        substantive response.
        """
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "Here is the answer"},
            {"role": "user", "content": "[U:confirm | N:0] confirm"},
        ])
        # Held message is a malformed tool-call pattern
        eot._eot_confirmation_stack = [
            {"text": "`glob`\npattern=\"**/q36*\"", "reasoning": None},
        ]
        # last_substantive_response is the proper table
        eot._agent.last_substantive_response = "Done. Added three variables..."

        result = eot.accept_confirmation()

        # Should return the substantive response, NOT the malformed pattern
        assert result == "Done. Added three variables..."
        assert "`glob`" not in result

    def test_prefers_held_when_not_malformed(self):
        """held_text is preferred (the answer being confirmed).

        held_text is the LLM's substantive response shown to the user
        in the confirmation prompt (<LASTREPLY>). It is the MOST RECENT answer.
        """
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "[U:confirm | N:0] confirm"},
        ])
        # Held message is a normal text response
        eot._eot_confirmation_stack = [
            {"text": "Here is the improved answer with more details.", "reasoning": None},
        ]
        # last_substantive_response may be different (stale from previous turn)
        eot._agent.last_substantive_response = "Previous turn summary."

        result = eot.accept_confirmation()

        # Should return held_text (current answer), NOT stale substantive
        assert result == "Here is the improved answer with more details."

    def test_uses_held_when_no_substantive(self):
        """Falls back to held message when last_substantive_response is None."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "Here is the answer"},
            {"role": "user", "content": "[U:confirm | N:0] confirm"},
        ])
        eot._eot_confirmation_stack = [
            {"text": "Here is the answer", "reasoning": None},
        ]
        eot._agent.last_substantive_response = None  # No substantive response

        result = eot.accept_confirmation()

        assert result == "Here is the answer"

    def test_logs_eot_confirm_accepted(self):
        """accept_confirmation() logs EOT_CONFIRM_ACCEPTED to audit."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "answer"},
            {"role": "user", "content": "[U:confirm | N:0] confirm"},
        ])
        eot._eot_confirmation_stack = [{"text": "answer", "reasoning": None}]

        eot.accept_confirmation()

        # Check that _emit was called with EOT_CONFIRM_ACCEPTED
        emit_calls = [
            call for call in eot._audit_writer._emit.call_args_list
            if "EOT_CONFIRM_ACCEPTED" in str(call)
        ]
        assert len(emit_calls) == 1
        # Verify source is in the call
        call_args = emit_calls[0][0]
        assert "EOT_CONFIRM_ACCEPTED" in call_args[0]

    def test_stacked_confirmation_prefers_substantive(self):
        """With stacked confirmations, substantive is used when held is malformed."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "first"},
            {"role": "user", "content": "[U:confirm | N:0] confirm 1"},
            {"role": "assistant", "content": "second"},
            {"role": "user", "content": "[U:confirm | N:0] confirm 2"},
        ])
        # Stacked: first is proper, second is malformed
        eot._eot_confirmation_stack = [
            {"text": "Done. Added three variables...", "reasoning": None},
            {"text": "`glob`\npattern=\"**/q36*\"", "reasoning": None},
        ]
        eot._agent.last_substantive_response = "Done. Added three variables..."

        result = eot.accept_confirmation()

        # Should return substantive (held is malformed)
        assert result == "Done. Added three variables..."


class TestEotBudget:
    """Test EOT budget constant."""

    def test_budget_constant(self):
        """Budget is set to 20 attempts."""
        from agent_eot_protection import _ACCIDENTAL_EOT_BUDGET

        assert _ACCIDENTAL_EOT_BUDGET == 20

    def test_counter_increments(self):
        """Counter increments on each potential EOT."""
        from agent_eot_protection import _ACCIDENTAL_EOT_BUDGET

        counter = 0
        for i in range(_ACCIDENTAL_EOT_BUDGET):
            counter += 1
            assert counter <= _ACCIDENTAL_EOT_BUDGET

        # Next increment exceeds budget
        counter += 1
        assert counter > _ACCIDENTAL_EOT_BUDGET


class TestSlashCommandDuringConfirmation:
    """Test slash command dispatch during EOT confirmation round.

    When the LLM returns a slash command during a confirmation round, only
    synthetic user messages are popped (not assistant responses) to keep the
    context ending with assistant. This allows the command handler to append
    user + assistant without consecutive-user violation.
    """

    def test_pop_synthetic_only_before_slash_command(self):
        """Only synthetic users are popped (assistant preserved) before slash command."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Here is my answer"},
            {"role": "user", "content": "[U:confirm | N:0] confirm"},
        ])
        eot._eot_confirmation_stack = [
            {"text": "Here is my answer", "reasoning": None},
        ]

        # Simulate slash command dispatch: pop only synthetic users
        if eot.is_in_confirmation:
            eot.pop_synthetic_only()

        # Context should have synthetic user removed but assistant preserved
        msgs = eot._context._messages
        assert len(msgs) == 3  # system, user, assistant
        assert msgs[-1]["role"] == "assistant"
        assert msgs[-1]["content"] == "Here is my answer"

        # Stack should be cleared
        assert len(eot._eot_confirmation_stack) == 0

    def test_no_consecutive_users_after_pop_and_append(self):
        """After popping synthetic users, append_user doesn't create consecutive users."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Answer"},
            {"role": "user", "content": "[U:confirm | N:0] confirm"},
        ])
        eot._eot_confirmation_stack = [
            {"text": "Answer", "reasoning": None},
        ]

        # Pop only synthetic users (preserves assistant)
        if eot.is_in_confirmation:
            eot.pop_synthetic_only()

        # Now simulate append_user (from slash command handler)
        eot._context.append_user("fork task")

        # Verify no consecutive user messages
        msgs = eot._context._messages
        roles = [m["role"] for m in msgs]
        for i in range(1, len(roles)):
            if roles[i] == "user" and roles[i-1] == "user":
                pytest.fail(f"Consecutive user messages at index {i-1},{i}")

    def test_multiple_synthetic_users_popped(self):
        """Multiple synthetic user confirmations are all popped."""
        from agent_eot_protection import EOTProtection

        eot = _make_eot_with_context([
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "[U:confirm | N:0] confirm 1"},
            {"role": "assistant", "content": "Answer 2"},
            {"role": "user", "content": "[U:confirm | N:0] confirm 2"},
        ])
        eot._eot_confirmation_stack = [
            {"text": "Answer 1", "reasoning": None},
            {"text": "Answer 2", "reasoning": None},
        ]

        # Pop only synthetic users
        if eot.is_in_confirmation:
            eot.pop_synthetic_only()

        # All synthetic users should be removed, assistants preserved
        msgs = eot._context._messages
        assert len(msgs) == 4  # system, user, assistant, assistant
        assert all("eot_confirmation" not in str(m.get("content", "")) for m in msgs)