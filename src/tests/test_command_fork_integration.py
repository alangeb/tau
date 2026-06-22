"""Test for agent command execution and subagent/fork integration.

This test validates that the command chaining mechanism works correctly
and that fork commands properly invoke the subagent system with the correct context.
"""

from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestCommandExecution:
    """Test command execution and subagent integration."""

    def test_command_chain_triggers_fork(self, test_config):
        """Verify that /fork commands trigger subagent execution with correct parameters."""
        from agent_core import TauErgon
        from agent_input import InputHandler, InputMessage
        from agent_models import SubAgentResult
        from unittest.mock import patch

        agent = TauErgon(
            config=test_config,
            base_url="http://test:8000/v1",
            model="test-model",
            max_context_tokens=200000,
        )

        handler = InputHandler(agent)

        # Patch where it's USED (agent_command_handlers imports from agent_subagent)
        with patch("agent_command_handlers.invoke_fork_sync") as mock_fork:
            mock_fork.return_value = SubAgentResult(
                output="Result from forked subagent", input_tokens=50, output_tokens=25
            )

            # Execute /fork command with task
            msg = InputMessage.from_interactive(
                "/fork Analyze the current project structure"
            )
            handler._process_input(msg)

            # Verify fork was called with correct task
            assert mock_fork.called, "invoke_fork_sync should be called"
            call_kwargs = mock_fork.call_args[1]
            task = call_kwargs.get("prompt", "")

            # Verify the task contains the expected text
            assert "Analyze" in task, f"Task should contain 'Analyze': {task}"
            assert (
                "project structure" in task.lower()
            ), f"Task should contain 'project structure': {task}"
            assert mock_fork.call_count == 1, "Fork should be called exactly once"

    def test_fork_mode_passes_correct_parameters(self, test_config):
        """Verify that fork commands pass correct parameters."""
        from agent_core import TauErgon
        from agent_input import InputHandler, InputMessage
        from unittest.mock import patch
        from agent_models import SubAgentResult

        agent = TauErgon(
            config=test_config,
            base_url="http://test:8000/v1",
            model="test-model",
            max_context_tokens=200000,
        )

        handler = InputHandler(agent)

        # Patch where it's USED (agent_command_handlers imports from agent_subagent)
        with patch("agent_command_handlers.invoke_fork_sync") as mock_fork:
            mock_fork.return_value = SubAgentResult(
                output="Result", input_tokens=10, output_tokens=5
            )

            # Execute /fork command
            msg = InputMessage.from_interactive("/fork Review code")
            handler._process_input(msg)

            # Verify fork was called
            assert mock_fork.called
            call_kwargs = mock_fork.call_args[1]
            # Verify parent_context was passed
            assert (
                "parent_context" in call_kwargs
            ), "parent_context should be passed to fork"
            assert (
                "parent_agent" in call_kwargs
            ), "parent_agent should be passed to fork"


class TestSubagentIntegration:
    """Test subagent integration with agent commands."""

    def test_subagent_command_creates_isolated_context(self, test_config):
        """Verify that /subagent creates isolated context without parent history."""
        from agent_core import TauErgon
        from agent_input import InputHandler, InputMessage
        from agent_context import TauContext
        from unittest.mock import patch
        from agent_models import SubAgentResult

        agent = TauErgon(
            config=test_config,
            base_url="http://test:8000/v1",
            model="test-model",
            max_context_tokens=200000,
        )

        # Add some initial context
        agent.context = TauContext(
            [
                {"role": "system", "content": "Initial system prompt"},
                {"role": "user", "content": "User question 1"},
                {"role": "assistant", "content": "Answer 1"},
            ]
        )

        handler = InputHandler(agent)

        # Patch where it's USED (agent_command_handlers imports from agent_subagent)
        with patch("agent_command_handlers.invoke_subagent_sync") as mock_subagent:
            mock_subagent.return_value = SubAgentResult(
                output="Subagent result", input_tokens=30, output_tokens=15
            )

            # Execute /subagent command
            msg = InputMessage.from_interactive("/subagent Solve a math problem")
            handler._process_input(msg)

            # Verify subagent was called
            assert mock_subagent.called
            call_kwargs = mock_subagent.call_args[1]
            # Verify parent_context was NOT passed (isolated context)
            assert (
                call_kwargs.get("parent_context") is None
            ), "parent_context should be None for isolated subagent"
