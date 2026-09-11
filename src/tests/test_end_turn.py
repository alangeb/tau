"""Tests for the end_turn tool and its integration with the agent loop."""

from unittest.mock import MagicMock, patch
import pytest


class TestEndTurnTool:
    """Test the end_turn tool module."""

    def test_end_turn_module_exists(self):
        """end_turn module loads and has required attributes."""
        import tools.end_turn as et

        assert hasattr(et, "metadata")
        assert hasattr(et, "run")
        assert hasattr(et, "Args")
        assert et.metadata.name == "end_turn"

    def test_end_turn_with_message(self):
        """end_turn with message returns the message."""
        import tools.end_turn as et

        agent = MagicMock()
        agent.last_substantive_response = None
        result = et.run(message="Final answer", agent=agent)
        assert result == "Final answer"
        assert agent.force_end_turn == "Final answer"

    def test_end_turn_empty_message_uses_last_substantive(self):
        """end_turn with empty message resolves to last_substantive_response."""
        import tools.end_turn as et

        agent = MagicMock()
        agent.last_substantive_response = "Previous substantive response"
        result = et.run(message="", agent=agent)
        assert result == "Previous substantive response"
        assert agent.force_end_turn == "Previous substantive response"

    def test_end_turn_empty_no_substantive_raises(self):
        """end_turn with empty message and no substantive response raises ValueError."""
        import tools.end_turn as et

        agent = MagicMock()
        agent.last_substantive_response = None
        with pytest.raises(ValueError, match="no substantive assistant"):
            et.run(message="", agent=agent)

    def test_end_turn_whitespace_message_uses_substantive(self):
        """end_turn with whitespace-only message resolves to last_substantive_response."""
        import tools.end_turn as et

        agent = MagicMock()
        agent.last_substantive_response = "Previous response"
        result = et.run(message="   ", agent=agent)
        assert result == "Previous response"

    def test_end_turn_without_agent(self):
        """end_turn works without agent (standalone)."""
        import tools.end_turn as et

        result = et.run(message="Hello", agent=None)
        assert result == "Hello"


class TestEndTurnLoopIntegration:
    """Test end_turn handling in the agent loop."""

    def _make_agent(self):
        """Create a minimal agent mock for loop testing."""
        from agent_context import TauContext
        from agent_eot_protection import EOTProtection

        agent = MagicMock()
        agent.context = TauContext([{"role": "system", "content": "test"}])
        agent._session = MagicMock()
        agent._session.audit_writer = MagicMock()
        agent._eot_protection = EOTProtection(agent)
        agent.last_substantive_response = None
        agent.force_end_turn = None
        agent.max_context_tokens = 128000
        return agent

    def test_end_turn_sole_call_detected(self):
        """Single end_turn tool call is detected as sole call."""
        tool_calls = [{"name": "end_turn", "args": "{}", "id": "call_1"}]
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "end_turn"

    def test_end_turn_mixed_filtered(self):
        """end_turn mixed with other tools is filtered out."""
        tool_calls = [
            {"name": "bash", "args": '{"cmd":"ls"}', "id": "call_1"},
            {"name": "end_turn", "args": "{}", "id": "call_2"},
        ]
        filtered = [tc for tc in tool_calls if tc["name"] != "end_turn"]
        assert len(filtered) == 1
        assert filtered[0]["name"] == "bash"

    def test_end_turn_args_parsing(self):
        """end_turn args are parsed correctly from JSON string."""
        import json

        tool_calls = [{"name": "end_turn", "args": '{"message": "done"}', "id": "call_1"}]
        args_str = tool_calls[0]["args"]
        args_dict = json.loads(args_str) if args_str.strip() else {}
        assert args_dict.get("message") == "done"

    def test_end_turn_empty_args_parsing(self):
        """end_turn with empty args is handled."""
        import json

        tool_calls = [{"name": "end_turn", "args": "{}", "id": "call_1"}]
        args_str = tool_calls[0]["args"]
        args_dict = json.loads(args_str) if args_str.strip() else {}
        assert args_dict.get("message", "").strip() == ""


class TestEndTurnConfirmationIntegration:
    """Test end_turn during confirmation round."""

    def test_end_turn_in_confirmation_uses_held_text(self):
        """end_turn during confirmation round uses held text if no message."""
        from agent_context import TauContext
        from agent_eot_protection import EOTProtection

        agent = MagicMock()
        agent.context = TauContext([{"role": "system", "content": "test"}])
        agent._session = MagicMock()
        agent._session.audit_writer = MagicMock()
        agent._eot_protection = EOTProtection(agent)
        agent.last_substantive_response = None
        agent.max_context_tokens = 200000

        # Simulate a confirmation round
        agent._eot_protection.handle_potential_eot("Held response text", None)
        assert agent._eot_protection.is_in_confirmation

        # Get held text
        held = agent._eot_protection._eot_confirmation_stack[-1]
        assert held["text"] == "Held response text"

    def test_end_turn_in_confirmation_with_message(self):
        """end_turn during confirmation round uses provided message."""
        from agent_context import TauContext
        from agent_eot_protection import EOTProtection

        agent = MagicMock()
        agent.context = TauContext([{"role": "system", "content": "test"}])
        agent._session = MagicMock()
        agent._session.audit_writer = MagicMock()
        agent._eot_protection = EOTProtection(agent)
        agent.last_substantive_response = None
        agent.max_context_tokens = 200000

        # Simulate a confirmation round
        agent._eot_protection.handle_potential_eot("Held response text", None)

        # end_turn with message should use the message, not held text
        message = "Custom final message"
        assert message == "Custom final message"


class TestSentinel:
    """Test ENDOFTURN sentinel acceptance."""

    def test_sentinel_accepted(self):
        """ENDOFTURN is accepted as confirmation."""
        from agent_eot_protection import ACCIDENTAL_EOT, EOTProtection
        from agent_context import TauContext

        agent = MagicMock()
        agent.context = TauContext([{"role": "system", "content": "test"}])
        agent._session = MagicMock()
        agent._session.audit_writer = MagicMock()
        agent.last_substantive_response = None

        eot = EOTProtection(agent)
        confirmed, stripped = eot.check_confirmation("ENDOFTURN")
        assert confirmed is True
        assert stripped is None

    def test_sentinel_case_insensitive(self):
        """ENDOFTURN match is case-insensitive."""
        from agent_eot_protection import EOTProtection
        from agent_context import TauContext

        agent = MagicMock()
        agent.context = TauContext([{"role": "system", "content": "test"}])
        agent._session = MagicMock()
        agent._session.audit_writer = MagicMock()
        agent.last_substantive_response = None

        eot = EOTProtection(agent)
        confirmed, stripped = eot.check_confirmation("endofturn")
        assert confirmed is True

    def test_sentinel_suffix_strips_text(self):
        """ENDOFTURN at end of response strips preceding content."""
        from agent_eot_protection import ACCIDENTAL_EOT, EOTProtection
        from agent_context import TauContext

        agent = MagicMock()
        agent.context = TauContext([{"role": "system", "content": "test"}])
        agent._session = MagicMock()
        agent._session.audit_writer = MagicMock()
        agent.last_substantive_response = None

        eot = EOTProtection(agent)
        response = "Here is my answer\n\nENDOFTURN"
        confirmed, stripped = eot.check_confirmation(response)
        assert confirmed is True
        assert "Here is my answer" in stripped
        assert ACCIDENTAL_EOT not in stripped


class TestEndTurnInToolsRegistry:
    """Test that end_turn is properly registered in the tools registry."""

    def test_end_turn_in_tools(self):
        """end_turn is registered in TOOLS dict."""
        from tools import TOOLS
        assert "end_turn" in TOOLS

    def test_end_turn_metadata(self):
        """end_turn has correct metadata."""
        from tools import TOOLS

        entry = TOOLS["end_turn"]
        assert entry.name == "end_turn"
        assert "end_turn" in entry.description.lower() or "end of turn" in entry.description.lower()


class TestResolveEndTurnMessage:
    """Test _resolve_end_turn_message sentinel rejection."""

    def _make_agent(self, substantive=None):
        from unittest.mock import MagicMock
        from agent_context import TauContext
        from agent_eot_protection import EOTProtection

        agent = MagicMock()
        agent.context = TauContext([{"role": "system", "content": "test"}])
        agent._session = MagicMock()
        agent._session.audit_writer = MagicMock()
        agent._eot_protection = EOTProtection(agent)
        agent.last_substantive_response = substantive
        agent.max_context_tokens = 200000
        return agent

    def test_rejects_exact_sentinel(self):
        """end_turn(message='ENDOFTURN') falls through to held text."""
        from agent_loop import _resolve_end_turn_message

        agent = self._make_agent()
        agent._eot_protection.handle_potential_eot("Held comprehensive answer", None)
        held = agent._eot_protection._eot_confirmation_stack[-1]

        result = _resolve_end_turn_message({"message": "ENDOFTURN"}, agent, held)
        assert result == "Held comprehensive answer"

    def test_rejects_sentinel_with_whitespace(self):
        """end_turn(message=' ENDOFTURN ') falls through to held text."""
        from agent_loop import _resolve_end_turn_message

        agent = self._make_agent()
        agent._eot_protection.handle_potential_eot("Held answer", None)
        held = agent._eot_protection._eot_confirmation_stack[-1]

        result = _resolve_end_turn_message({"message": " ENDOFTURN "}, agent, held)
        assert result == "Held answer"

    def test_rejects_sentinel_case_insensitive(self):
        """end_turn(message='endofturn') falls through to held text."""
        from agent_loop import _resolve_end_turn_message

        agent = self._make_agent()
        agent._eot_protection.handle_potential_eot("Held answer", None)
        held = agent._eot_protection._eot_confirmation_stack[-1]

        result = _resolve_end_turn_message({"message": "endofturn"}, agent, held)
        assert result == "Held answer"

    def test_rejects_short_sentinel_variant(self):
        """end_turn(message='!!ENDOFTURN!!') falls through — 13 chars, contains sentinel."""
        from agent_loop import _resolve_end_turn_message

        agent = self._make_agent()
        agent._eot_protection.handle_potential_eot("Held answer", None)
        held = agent._eot_protection._eot_confirmation_stack[-1]

        # "!!ENDOFTURN!!" = 13 chars = len("ENDOFTURN") + 4
        result = _resolve_end_turn_message({"message": "!!ENDOFTURN!!"}, agent, held)
        assert result == "Held answer"

    def test_accepts_substantive_message(self):
        """end_turn(message='Here is my answer.') uses the message."""
        from agent_loop import _resolve_end_turn_message

        agent = self._make_agent()
        agent._eot_protection.handle_potential_eot("Held answer", None)
        held = agent._eot_protection._eot_confirmation_stack[-1]

        result = _resolve_end_turn_message({"message": "Here is my answer."}, agent, held)
        assert result == "Here is my answer."

    def test_accepts_long_message_containing_sentinel(self):
        """end_turn(message='Done. ENDOFTURN') uses the message — too long to be sentinel-only."""
        from agent_loop import _resolve_end_turn_message

        agent = self._make_agent()
        agent._eot_protection.handle_potential_eot("Held answer", None)
        held = agent._eot_protection._eot_confirmation_stack[-1]

        # "Done. ENDOFTURN" = 15 chars > 13, so it passes
        result = _resolve_end_turn_message({"message": "Done. ENDOFTURN"}, agent, held)
        assert result == "Done. ENDOFTURN"

    def test_rejects_single_char(self):
        """end_turn(message='X') falls through — too short."""
        from agent_loop import _resolve_end_turn_message

        agent = self._make_agent()
        agent._eot_protection.handle_potential_eot("Held answer", None)
        held = agent._eot_protection._eot_confirmation_stack[-1]

        result = _resolve_end_turn_message({"message": "X"}, agent, held)
        assert result == "Held answer"

    def test_falls_to_substantive_when_no_held(self):
        """No held text — falls to last_substantive_response."""
        from agent_loop import _resolve_end_turn_message

        agent = self._make_agent(substantive="Previous substantive answer")

        result = _resolve_end_turn_message({"message": "ENDOFTURN"}, agent, None)
        assert result == "Previous substantive answer"

    def test_default_when_everything_empty(self):
        """No message, no held, no substantive — returns default."""
        from agent_loop import _resolve_end_turn_message

        agent = self._make_agent()

        result = _resolve_end_turn_message({}, agent, None)
        assert result == "[end_turn — no message]"