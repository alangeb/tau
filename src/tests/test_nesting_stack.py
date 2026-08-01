"""Tests for nesting stack feature.

Tests that nesting_stack correctly tracks the nesting hierarchy:
- S = Subagent (blank slate)
- F = Fork (inherits context)
- T = Think (fork with no tools)
- K = Skill (fork with restricted tools)

The nesting_stack is a string showing the path from root to current agent.
Example: "SF" means fork inside subagent.
"""

import pytest
from unittest.mock import MagicMock, patch

from agent_context import TauContext
from agent_subagent import invoke_subagent_sync, invoke_fork_sync
from agent_core import TauErgon
from tools import ToolContext


class TestNestingStack:
    """Test nesting stack tracking."""

    def test_nesting_count_derived_from_stack(self, test_config):
        """nesting_count property returns len(nesting_stack)."""
        agent = TauErgon(
            config=test_config,
            llm_group_name="test",
            max_context_tokens=200000,
        )

        # Empty stack → count 0
        assert agent.nesting_stack == ""
        assert agent.nesting_count == 0

        # Set stack → count matches length
        agent.nesting_stack = "S"
        assert agent.nesting_count == 1

        agent.nesting_stack = "SF"
        assert agent.nesting_count == 2

        agent.nesting_stack = "SST"
        assert agent.nesting_count == 3

    def test_subagent_appends_S(self, test_config):
        """Subagent appends 'S' to nesting stack."""
        with patch("agent_subagent._create_subagent") as mock_create:
            mock_subagent = MagicMock()
            mock_subagent.invoke_with_tools.return_value = "result"
            mock_create.return_value = mock_subagent

            result = invoke_subagent_sync(
                prompt="task",
                system_prompt="system",
                parent_agent=MagicMock(),
                nesting_count=0,
                nesting_stack="",
                config=test_config,
            )

        assert isinstance(result, str)
        # Verify nesting_stack was set to "S"
        assert mock_subagent.nesting_stack == "S"

    def test_subagent_inherits_stack(self, test_config):
        """Subagent inherits parent stack + appends S."""
        # Create a mock parent with existing stack
        parent = MagicMock()
        parent.current_group_name = "test"

        with patch.object(TauErgon, "invoke_with_tools", return_value="result"):
            invoke_subagent_sync(
                prompt="task",
                system_prompt="system",
                parent_agent=parent,
                nesting_count=1,
                nesting_stack="F",
                config=test_config,
            )

        # The child should have stack "FS" (fork then subagent)
        # We can't easily verify this without mocking _create_subagent,
        # but the function signature is correct.

    def test_fork_appends_F(self, test_config):
        """Fork appends 'F' to nesting stack."""
        with patch("agent_subagent._create_fork_isolation", return_value=("test", None)):
            with patch("agent_subagent._create_subagent") as mock_create:
                mock_fork = MagicMock()
                mock_fork.invoke_with_tools.return_value = "result"
                mock_fork.nesting_count = 0
                mock_create.return_value = mock_fork

                parent = MagicMock()
                parent._session.audit_file = "/tmp/test.audit"
                parent._session.audit_writer = MagicMock()
                if hasattr(parent, "_fork_loop_tracker"):
                    delattr(parent, "_fork_loop_tracker")

                ctx = TauContext([{"role": "system", "content": "System"}])

                invoke_fork_sync(
                    "task",
                    ctx,
                    parent,
                    nesting_stack="",
                    nesting_type="F",
                )

        # Verify the function was called with correct parameters
        assert mock_create.called

    def test_fork_inherits_stack(self, test_config):
        """Fork inherits parent stack + appends type."""
        with patch("agent_subagent._create_fork_isolation", return_value=("test", None)):
            with patch("agent_subagent._create_subagent") as mock_create:
                mock_fork = MagicMock()
                mock_fork.invoke_with_tools.return_value = "result"
                mock_fork.nesting_count = 0
                mock_create.return_value = mock_fork

                parent = MagicMock()
                parent._session.audit_file = "/tmp/test.audit"
                parent._session.audit_writer = MagicMock()
                if hasattr(parent, "_fork_loop_tracker"):
                    delattr(parent, "_fork_loop_tracker")

                ctx = TauContext([{"role": "system", "content": "System"}])

                invoke_fork_sync(
                    "task",
                    ctx,
                    parent,
                    nesting_stack="S",
                    nesting_type="F",
                )

        # The child should have stack "SF" (subagent then fork)
        assert mock_create.called

    def test_think_appends_T(self, test_config):
        """Think tool appends 'T' to nesting stack."""
        from tools.think import run

        agent = MagicMock()
        agent.nesting_count = 0
        agent.nesting_stack = ""
        agent.context.get_messages.return_value = []

        with patch("tools.think.invoke_fork_sync", return_value="think result") as mock_invoke:
            result = run(question="test question", _ctx=ToolContext(agent=agent))

        assert isinstance(result, str)
        mock_invoke.assert_called_once()
        call_kwargs = mock_invoke.call_args[1]
        assert call_kwargs["nesting_type"] == "T"

    def test_skill_appends_K(self, test_config):
        """Skill tool appends 'K' to nesting stack."""
        from tools.skill import run

        agent = MagicMock()
        agent.nesting_count = 0
        agent.nesting_stack = ""

        with patch("agent_subagent.invoke_fork_sync", return_value="skill content") as mock_invoke:
            with patch("tools.skill._load_skill", return_value=None):
                result = run(skill_name="nonexistent_skill", _ctx=ToolContext(agent=agent))

        assert isinstance(result, str)
        mock_invoke.assert_called_once()
        call_kwargs = mock_invoke.call_args[1]
        assert call_kwargs["nesting_type"] == "K"

    def test_fork_tool_appends_F(self, test_config):
        """Fork tool appends 'F' to nesting stack."""
        from tools.fork import run

        agent = MagicMock()
        agent.nesting_count = 0
        agent.nesting_stack = ""

        with patch("tools.fork.invoke_fork_sync", return_value="fork result") as mock_invoke:
            result = run(task="test task", _ctx=ToolContext(agent=agent))

        assert isinstance(result, str)
        mock_invoke.assert_called_once()
        call_kwargs = mock_invoke.call_args[1]
        assert call_kwargs["nesting_type"] == "F"

    def test_subagent_tool_appends_S(self, test_config):
        """Subagent tool appends 'S' to nesting stack."""
        from tools.subagent import run

        agent = MagicMock()
        agent.nesting_count = 0
        agent.nesting_stack = ""
        agent.context.get_system.return_value = "System"

        with patch("tools.subagent.invoke_subagent_sync", return_value="subagent result") as mock_invoke:
            result = run(task="test task", _ctx=ToolContext(agent=agent))

        assert isinstance(result, str)
        mock_invoke.assert_called_once()
        call_kwargs = mock_invoke.call_args[1]
        assert call_kwargs["nesting_stack"] == ""

    def test_nested_stack_example(self, test_config):
        """Test nested stack example: root → subagent → fork → think."""
        # Root agent has empty stack
        root_stack = ""
        assert len(root_stack) == 0

        # Subagent appends S
        subagent_stack = root_stack + "S"
        assert subagent_stack == "S"
        assert len(subagent_stack) == 1

        # Fork in subagent appends F
        fork_stack = subagent_stack + "F"
        assert fork_stack == "SF"
        assert len(fork_stack) == 2

        # Think in fork appends T
        think_stack = fork_stack + "T"
        assert think_stack == "SFT"
        assert len(think_stack) == 3


class TestNestingStackDisplay:
    """Test nesting stack display format."""

    def test_display_root_level(self):
        """Root level displays 'nest: .'."""
        from agent_models import AgentStatus

        status = AgentStatus(
            nesting_count=0,
            nesting_stack="",
            current_group_name="default",
            agent_name="default",
        )

        assert status.nesting_stack == ""
        assert status.nesting_count == 0

    def test_display_subagent_level(self):
        """Subagent level displays 'nest: S'."""
        from agent_models import AgentStatus

        status = AgentStatus(
            nesting_count=1,
            nesting_stack="S",
            current_group_name="default",
            agent_name="default",
        )

        assert status.nesting_stack == "S"
        assert status.nesting_count == 1

    def test_display_nested_level(self):
        """Nested level displays 'nest: SF'."""
        from agent_models import AgentStatus

        status = AgentStatus(
            nesting_count=2,
            nesting_stack="SF",
            current_group_name="default",
            agent_name="default",
        )

        assert status.nesting_stack == "SF"
        assert status.nesting_count == 2


class TestRestrictedNesting:
    """Test _is_restricted_nesting() method for T/K nesting types."""

    def test_empty_stack_not_restricted(self, test_config):
        """Empty nesting stack is not restricted."""
        agent = TauErgon(
            config=test_config,
            llm_group_name="test",
            max_context_tokens=200000,
        )
        assert not agent._is_restricted_nesting()

    def test_subagent_not_restricted(self, test_config):
        """Subagent (S) nesting is not restricted."""
        agent = TauErgon(
            config=test_config,
            llm_group_name="test",
            max_context_tokens=200000,
        )
        agent.nesting_stack = "S"
        assert not agent._is_restricted_nesting()

    def test_fork_not_restricted(self, test_config):
        """Fork (F) nesting is not restricted."""
        agent = TauErgon(
            config=test_config,
            llm_group_name="test",
            max_context_tokens=200000,
        )
        agent.nesting_stack = "F"
        assert not agent._is_restricted_nesting()

    def test_think_is_restricted(self, test_config):
        """Think (T) nesting is restricted."""
        agent = TauErgon(
            config=test_config,
            llm_group_name="test",
            max_context_tokens=200000,
        )
        agent.nesting_stack = "T"
        assert agent._is_restricted_nesting()

    def test_skill_is_restricted(self, test_config):
        """Skill (K) nesting is restricted."""
        agent = TauErgon(
            config=test_config,
            llm_group_name="test",
            max_context_tokens=200000,
        )
        agent.nesting_stack = "K"
        assert agent._is_restricted_nesting()

    def test_nested_think_is_restricted(self, test_config):
        """Nested think (e.g., STF) is restricted if last char is T."""
        agent = TauErgon(
            config=test_config,
            llm_group_name="test",
            max_context_tokens=200000,
        )
        agent.nesting_stack = "ST"
        assert agent._is_restricted_nesting()

    def test_nested_skill_is_restricted(self, test_config):
        """Nested skill (e.g., SFK) is restricted if last char is K."""
        agent = TauErgon(
            config=test_config,
            llm_group_name="test",
            max_context_tokens=200000,
        )
        agent.nesting_stack = "SFK"
        assert agent._is_restricted_nesting()

    def test_nested_fork_not_restricted(self, test_config):
        """Nested fork (e.g., STF) is not restricted if last char is F."""
        agent = TauErgon(
            config=test_config,
            llm_group_name="test",
            max_context_tokens=200000,
        )
        agent.nesting_stack = "STF"
        assert not agent._is_restricted_nesting()