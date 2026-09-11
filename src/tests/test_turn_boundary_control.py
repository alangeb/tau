"""Test control queue processing at turn boundaries in run_loop().

Verifies that _process_control_queue() is called at the top of the while loop
in run_loop(), so parent supervisor commands are processed before each LLM call.
"""

import json
from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

from agent_lifecycle import AgentLifecycle


def _make_llm_response(text="done", tool_calls=None, reasoning=None):
    """Build a mock LLM response object."""
    resp = MagicMock()
    resp.text = text
    resp.reasoning = reasoning or ""
    stats = MagicMock()
    stats.prompt_tokens = 10
    stats.completion_tokens = 5
    resp.stats = stats
    resp.tool_calls = tool_calls or []
    return resp


@pytest.fixture
def agent(test_config):
    """Create a TauErgon instance for control queue tests."""
    from agent_core import TauErgon

    with patch.object(TauErgon, "invoke_with_tools"):
        agent = TauErgon(
            config=test_config,
            base_url="http://test:8000/v1",
            model="test-model",
        )
    # Reset lifecycle state for clean tests
    AgentLifecycle._reset()
    # Disable early reflection to avoid tool call complexity
    agent.reflection_scheduler.cfg = replace(
        agent.reflection_scheduler.cfg, initial_think=False
    )
    return agent


class TestControlQueueProcessedEachTurn:
    """Test that control queue is checked before each LLM call."""

    def test_control_queue_processed_each_turn(self, agent):
        """Control queue should be checked before each LLM call."""
        agent._control_queue.put(json.dumps({
            "type": "inject", "role": "user", "content": "test message"
        }))

        # Mock LLM to return text (triggers EOT confirmation), then confirm
        with patch("agent_loop._invoke_llm_with_retry") as mock_invoke:
            mock_invoke.side_effect = [
                (_make_llm_response(text="Hello"), None),
                (_make_llm_response(text="ENDOFTURN"), None),
            ]

            from agent_loop import run_loop
            run_loop(agent)

            # Control queue should be empty (processed)
            assert agent._control_queue.empty()

    def test_inject_before_llm_call(self, agent):
        """Injected message should be in context when LLM is called."""
        agent._control_queue.put(json.dumps({
            "type": "inject", "role": "user", "content": "injected content"
        }))

        captured_contexts = []

        def capture_context(*args, **kwargs):
            # Capture context state when LLM is invoked
            captured_contexts.append([dict(msg) for msg in agent.context])
            return _make_llm_response(text="ENDOFTURN"), None

        with patch("agent_loop._invoke_llm_with_retry", side_effect=capture_context):
            from agent_loop import run_loop
            run_loop(agent)

        # LLM should have been called at least once
        assert len(captured_contexts) > 0
        # The injected content should be in the context when LLM was called
        first_context = captured_contexts[0]
        context_texts = [str(msg.get("content", "")) for msg in first_context]
        assert any("injected content" in t for t in context_texts)


class TestTerminateEndsLoop:
    """Test that terminate command ends the loop."""

    def test_terminate_forceful_ends_loop(self, agent):
        """Forceful terminate should end the loop immediately without LLM call."""
        AgentLifecycle._reset()
        agent._control_queue.put(json.dumps({
            "type": "terminate", "graceful": False
        }))

        with patch("agent_loop._invoke_llm_with_retry") as mock_invoke:
            from agent_loop import run_loop
            run_loop(agent)

            # LLM should NOT have been called
            mock_invoke.assert_not_called()

    def test_terminate_graceful_finishes_turn(self, agent):
        """Graceful terminate should inject summary request and finish turn."""
        AgentLifecycle._reset()
        agent._control_queue.put(json.dumps({
            "type": "terminate", "graceful": True
        }))

        # Mock LLM to return text, then confirm EOT
        with patch("agent_loop._invoke_llm_with_retry") as mock_invoke:
            mock_invoke.side_effect = [
                (_make_llm_response(text="Summary of work"), None),
                (_make_llm_response(text="ENDOFTURN"), None),
            ]

            from agent_loop import run_loop
            run_loop(agent)

            # force_end_turn should be set
            assert agent.force_end_turn == "external_terminate_graceful"


class TestMultipleCommandsProcessed:
    """Test that multiple commands are processed in one turn."""

    def test_multiple_commands_processed(self, agent):
        """Multiple commands should all be processed in one turn."""
        agent._control_queue.put(json.dumps({"type": "status"}))
        agent._control_queue.put(json.dumps({
            "type": "inject", "role": "user", "content": "test content"
        }))
        agent._control_queue.put(json.dumps({"type": "status"}))

        with patch("agent_loop._invoke_llm_with_retry") as mock_invoke:
            mock_invoke.side_effect = [
                (_make_llm_response(text="Response"), None),
                (_make_llm_response(text="ENDOFTURN"), None),
            ]

            from agent_loop import run_loop
            run_loop(agent)

            # Control queue should be empty (all processed)
            assert agent._control_queue.empty()

    def test_status_command_logged(self, agent):
        """Status command should log status without modifying context."""
        agent._control_queue.put(json.dumps({"type": "status"}))

        with patch("agent_loop._invoke_llm_with_retry") as mock_invoke:
            mock_invoke.side_effect = [
                (_make_llm_response(text="Response"), None),
                (_make_llm_response(text="ENDOFTURN"), None),
            ]

            from agent_loop import run_loop
            run_loop(agent)

            # Status command should not crash and queue should be empty
            assert agent._control_queue.empty()


class TestRedirectCommand:
    """Test that redirect command clears context and starts new task."""

    def test_redirect_clears_context(self, agent):
        """Redirect should clear context and add new task."""
        # Add some messages to context first
        agent.context.append_user("Original task")

        agent._control_queue.put(json.dumps({
            "type": "redirect", "task": "New task from parent"
        }))

        with patch("agent_loop._invoke_llm_with_retry") as mock_invoke:
            mock_invoke.side_effect = [
                (_make_llm_response(text="Response"), None),
                (_make_llm_response(text="ENDOFTURN"), None),
            ]

            from agent_loop import run_loop
            run_loop(agent)

            # Context should contain the new task
            context_texts = [str(msg.get("content", "")) for msg in agent.context]
            assert any("New task from parent" in t for t in context_texts)
            # Original task should not be in context (cleared)
            assert not any("Original task" in t for t in context_texts)
