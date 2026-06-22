"""Tests for agent_commands module.

Tests:
    test_command_discovery - Command discovery and validation
    test_command_content - Command content validation
    test_command_chaining - Command chaining syntax
    test_command_integration - Integration with InputHandler
    test_command_placeholder_substitution - Placeholder substitution
    test_command_file_loading - Command file loading
"""

import sys
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_command_registry import (
    substitute_placeholders,
    discover_commands,
    get_command,
    load_command_content,
    parse_multi_prompt,
)
from agent_core import TauErgon
from agent_input import InputHandler
from agent_models import InputMessage, SubAgentResult


class TestCommandDiscovery:
    """Test command discovery functionality."""

    def test_commands_discovered(self, commands_dir):
        """Verify commands are discovered."""
        commands = discover_commands(str(commands_dir))
        assert len(commands) > 0, "No commands found"

    def test_commands_have_required_fields(self, commands_dir):
        """Verify commands have required fields."""
        commands = discover_commands(str(commands_dir))
        for cmd in commands:
            assert "name" in cmd, f"Command missing 'name': {cmd}"
            assert "content" in cmd, f"Command missing 'content': {cmd}"
            assert "file_path" in cmd, f"Command missing 'file_path': {cmd}"
            assert "full_content" in cmd, f"Command missing 'full_content': {cmd}"

    def test_gitcrit_command_exists(self, commands_dir):
        """Verify /gitcrit command exists."""
        commands = discover_commands(str(commands_dir))
        names = [cmd["name"] for cmd in commands]
        assert "gitcrit" in names, "/gitcrit command not found"

    def test_command_type_is_command(self, commands_dir):
        """Verify all commands have type='command'."""
        commands = discover_commands(str(commands_dir))
        for cmd in commands:
            assert cmd["type"] == "command", f"Command {cmd['name']} has wrong type"

    def test_command_count_reasonable(self, commands_dir):
        """Verify reasonable number of commands."""
        commands = discover_commands(str(commands_dir))
        assert len(commands) > 5, "Expected more than 5 commands"


class TestCommandContent:
    """Test command content validation."""

    def test_gitcrit_command_content(self, commands_dir):
        """Verify /gitcrit command has expected content."""
        cmd = get_command("gitcrit", str(commands_dir))
        assert cmd is not None
        assert "critique" in cmd["content"].lower()

    def test_gitcrit_contains_critique(self, commands_dir):
        """Verify /gitcrit content contains critique instructions."""
        cmd = get_command("gitcrit", str(commands_dir))
        assert cmd is not None
        assert "critique" in cmd["content"].lower()

    def test_command_content_not_empty(self, commands_dir):
        """Verify all commands have non-empty content."""
        commands = discover_commands(str(commands_dir))
        for cmd in commands:
            assert (
                len(cmd["content"].strip()) > 0
            ), f"Command {cmd['name']} has empty content"

    def test_command_content_is_string(self, commands_dir):
        """Verify all command content is a string."""
        commands = discover_commands(str(commands_dir))
        for cmd in commands:
            assert isinstance(
                cmd["content"], str
            ), f"Command {cmd['name']} content is not a string"


class TestCommandPlaceholderSubstitution:
    """Test placeholder substitution in commands."""

    def test_single_placeholder(self):
        """Test $1 substitution."""
        content = "Run $1"
        args = ["arg1"]
        result = substitute_placeholders(content, args)
        assert result == "Run arg1"

    def test_multiple_placeholders(self):
        """Test $1 and $2 substitution."""
        content = "Run $1 and $2"
        args = ["arg1", "arg2"]
        result = substitute_placeholders(content, args)
        assert result == "Run arg1 and arg2"

    def test_all_args_placeholder(self):
        """Test $* (all args) substitution."""
        content = "Run $*"
        args = ["arg1", "arg2", "arg3"]
        result = substitute_placeholders(content, args)
        assert result == "Run arg1 arg2 arg3"

    def test_first_and_rest_placeholder(self):
        """Test $1+ (first arg and rest) substitution."""
        content = "Run $1 with $1+"
        args = ["main", "extra1", "extra2"]
        result = substitute_placeholders(content, args)
        assert result == "Run main with main extra1 extra2"

    def test_no_placeholders(self):
        """Test content with no placeholders."""
        content = "No placeholders here"
        args = ["arg1"]
        result = substitute_placeholders(content, args)
        assert result == "No placeholders here"

    def test_empty_args(self):
        """Test with empty args list - placeholders replaced with empty string."""
        content = "Run $1"
        args = []
        result = substitute_placeholders(content, args)
        # With no args, out-of-range placeholders are replaced with empty string
        assert result == "Run "

    def test_placeholder_out_of_range(self):
        """Test placeholder with index beyond args length."""
        content = "Run $5"
        args = ["arg1"]
        result = substitute_placeholders(content, args)
        # Should handle gracefully (empty or original)
        assert isinstance(result, str)


class TestCommandChaining:
    """Test command chaining functionality."""

    def test_fork_command_chains(self, commands_dir, test_config):
        """Verify /fork command works correctly."""

        agent = TauErgon(
            config=test_config,
            base_url="http://test:8000/v1",
            model="test-model",
            max_context_tokens=200000,
        )
        handler = InputHandler(agent)

        # Patch where invoke_fork_sync is USED (agent_command_handlers imported it)
        with patch("agent_command_handlers.invoke_fork_sync") as mock_fork:
            mock_fork.return_value = SubAgentResult(
                output="Fork result", input_tokens=10, output_tokens=5
            )

            # Process /fork command
            msg = InputMessage.from_interactive("/fork Analyze the code")
            handler._process_input(msg)

            # Verify fork was called
            assert mock_fork.called


class TestCommandFileLoading:
    """Test command file loading functionality."""

    def test_load_command_content(self, commands_dir):
        """Test loading command content from file."""
        content = load_command_content("heartbeat", str(commands_dir))
        assert content is not None
        assert len(content) > 0

    def test_load_nonexistent_command(self, commands_dir):
        """Test loading nonexistent command returns None."""
        cmd = get_command("nonexistent_command", str(commands_dir))
        assert cmd is None

    def test_command_file_path_correct(self, commands_dir):
        """Verify command file paths are correct."""
        commands = discover_commands(str(commands_dir))
        for cmd in commands:
            assert Path(
                cmd["file_path"]
            ).exists(), f"Command file not found: {cmd['file_path']}"


class TestParseMultiPrompt:
    """Test parse_multi_prompt function."""

    def test_single_prompt(self):
        """Test parsing a single prompt."""
        prompts = parse_multi_prompt("Hello world", [])
        assert len(prompts) == 1
        assert "Hello world" in prompts[0]

    def test_multiple_prompts(self):
        """Test parsing multiple prompts separated by ---."""
        prompts = parse_multi_prompt("First\n---\nSecond", [])
        assert len(prompts) == 2
        assert "First" in prompts[0]
        assert "Second" in prompts[1]

    def test_empty_prompt(self):
        """Test parsing empty prompt returns empty list."""
        prompts = parse_multi_prompt("", [])
        assert prompts == []

    def test_placeholder_substitution_in_prompts(self):
        """Test that placeholders are substituted in each prompt."""
        prompts = parse_multi_prompt("Hello $1\n---\nGoodbye $1", ["World"])
        assert len(prompts) == 2
        assert "Hello World" in prompts[0]
        assert "Goodbye World" in prompts[1]
