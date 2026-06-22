"""Tests for the tools system.

Tests:
    test_all_tools_registered - Verify all tools are properly registered
    test_tool_schema_validation - Verify tool schemas are valid
    test_tool_functionality - Basic functionality tests for key tools
    test_get_tool_module - Verify tool module access works correctly
    test_tool_names_unique - Verify all tool names are unique
    test_tool_descriptions_present - Verify all tools have descriptions
    test_tool_types - Verify all tools have correct type
    test_tool_args_schema - Verify tool args_schema structure
    test_tool_run_is_callable - Verify all tools have callable run functions
    test_tool_descriptions_not_empty - Verify descriptions are meaningful
"""

import sys
from pathlib import Path
from unittest.mock import Mock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import get_all_tools, get_tool_module


class TestAllToolsRegistered:
    """Test that all tools are properly registered."""

    def test_tools_not_empty(self):
        """Verify we have tools registered."""
        tools = get_all_tools()
        assert len(tools) > 0, "No tools found in registry"

    def test_tool_count_reasonable(self):
        """Verify we have a reasonable number of tools."""
        tools = get_all_tools()
        assert len(tools) >= 10, f"Expected at least 10 tools, got {len(tools)}"

    def test_all_tools_have_name(self):
        """Verify every tool has a name."""
        tools = get_all_tools()
        for tool in tools:
            assert "name" in tool, f"Tool missing name: {tool}"
            assert isinstance(tool["name"], str), f"Tool name is not a string: {tool}"
            assert len(tool["name"]) > 0, f"Tool name is empty: {tool}"

    def test_all_tools_have_description(self):
        """Verify every tool has a description."""
        tools = get_all_tools()
        for tool in tools:
            assert "description" in tool, f"Tool missing description: {tool}"
            assert isinstance(
                tool["description"], str
            ), f"Tool description is not a string: {tool}"
            assert len(tool["description"]) > 0, f"Tool description is empty: {tool}"

    def test_all_tools_have_run(self):
        """Verify every tool has a run function."""
        tools = get_all_tools()
        for tool in tools:
            assert "run" in tool, f"Tool missing run function: {tool}"
            assert callable(tool["run"]), f"Tool run is not callable: {tool['name']}"

    def test_all_tools_have_type(self):
        """Verify every tool has a type field."""
        tools = get_all_tools()
        for tool in tools:
            assert "type" in tool, f"Tool missing type: {tool}"

    def test_all_tool_types_are_tool(self):
        """Verify all tools have type='tool'."""
        tools = get_all_tools()
        for tool in tools:
            assert (
                tool["type"] == "tool"
            ), f"Tool has incorrect type: {tool['name']} -> {tool['type']}"


class TestExpectedTools:
    """Test that expected tools are registered."""

    def test_file_read_exists(self):
        """Verify file_read tool exists."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        assert "file_read" in tool_names

    def test_file_edit_exists(self):
        """Verify file_edit tool exists."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        assert "file_edit" in tool_names

    def test_glob_exists(self):
        """Verify glob tool exists."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        assert "glob" in tool_names

    def test_grep_exists(self):
        """Verify grep tool exists."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        assert "grep" in tool_names

    def test_wc_exists(self):
        """Verify wc tool exists."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        assert "wc" in tool_names

    def test_head_exists(self):
        """Verify head tool exists."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        assert "head" in tool_names

    def test_file_write_exists(self):
        """Verify file_write tool exists."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        assert "file_write" in tool_names

    def test_bash_exists(self):
        """Verify bash tool exists."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        assert "bash" in tool_names

    def test_fork_exists(self):
        """Verify fork tool exists."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        assert "fork" in tool_names

    def test_subagent_exists(self):
        """Verify subagent tool exists."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        assert "subagent" in tool_names

    def test_pyscan_exists(self):
        """Verify pyscan tool exists."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        assert "pyscan" in tool_names

    def test_pyanalyze_exists(self):
        """Verify pyanalyze tool exists."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        assert "pyanalyze" in tool_names

    def test_skill_exists(self):
        """Verify skill tool exists."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        assert "skill" in tool_names


class TestToolSchemaValidation:
    """Test tool schema validation."""

    def test_tools_with_args_schema_are_dataclasses(self):
        """Verify tools with args_schema have valid JSON Schema structure."""
        tools = get_all_tools()
        for tool in tools:
            if "args_schema" in tool:
                schema = tool["args_schema"]
                assert isinstance(
                    schema, dict
                ), f"Schema for {tool['name']} is not a dict"
                assert "type" in schema, f"Schema for {tool['name']} missing 'type'"
                assert "properties" in schema, f"Schema for {tool['name']} missing 'properties'"

    def test_tools_without_args_schema_are_ok(self):
        """Verify tools without args_schema don't cause issues."""
        tools = get_all_tools()
        # Some tools may not have args_schema - this is OK
        any("args_schema" in tool for tool in tools)  # noqa: F841
        # Just verify we can iterate without errors
        assert isinstance(tools, list)


class TestGetToolModule:
    """Test tool module access."""

    def test_file_read_module_exists(self):
        """Verify we can get file_read module."""
        file_read_module = get_tool_module("file_read")
        assert file_read_module is not None, "Could not get file_read module"
        assert hasattr(file_read_module, "metadata"), "Module missing metadata attribute"
        assert file_read_module.metadata.name == "file_read", "Module name mismatch"

    def test_nonexistent_tool_returns_none(self):
        """Verify non-existent tool returns None."""
        fake_module = get_tool_module("non_existent_tool")
        assert fake_module is None, "Should return None for non-existent tool"

    def test_multiple_modules_accessible(self):
        """Verify multiple modules can be accessed."""
        file_read = get_tool_module("file_read")
        grep = get_tool_module("grep")
        glob = get_tool_module("glob")
        assert file_read is not None
        assert grep is not None
        assert glob is not None


class TestToolBasicFunctionality:
    """Test basic tool functionality."""

    def test_file_write_and_read(self, temp_dir):
        """Test file_write and file_read work together."""
        from pathlib import Path
        from tools import file_read, file_write

        # Use a path within cwd to avoid sandbox rejection
        test_file = Path.cwd() / ".test_tmp" / "test_file.txt"

        try:
            # Create mock agent
            mock_agent = Mock()
            mock_agent.log_file = None
            mock_agent.audit_file = None
            mock_agent.context_file = None
            mock_agent.max_context_tokens = 100000
            mock_agent._sandbox_last_call = None

            # Write test content
            result = file_write.run(
                file_path=str(test_file),
                content="Hello, world!",
                agent=mock_agent,
                tool_call_id="test-tool-call-id",
            )
            assert "ERROR" not in result, f"file_write should succeed, got: {result}"
            assert test_file.exists(), "File should be created"

            # Read it back
            result = file_read.run(
                file_path=str(test_file),
                offset=1,
                limit=100,
                agent=mock_agent,
                tool_call_id="test-tool-call-id-2",
            )
            assert "Hello, world!" in result, f"Content not found in result: {result}"

        finally:
            if test_file.exists():
                test_file.unlink()
            try:
                (Path.cwd() / ".test_tmp").rmdir()
            except OSError:
                pass

    def test_file_write_creates_parent_dirs(self, temp_dir):
        """Test file_write creates parent directories."""
        from pathlib import Path
        from tools import file_write

        # Use a path within cwd to avoid sandbox rejection
        test_file = Path.cwd() / ".test_tmp" / "subdir" / "nested" / "test.txt"

        try:
            mock_agent = Mock()
            mock_agent.log_file = None
            mock_agent.audit_file = None
            mock_agent.context_file = None
            mock_agent.max_context_tokens = 100000
            mock_agent._sandbox_last_call = None

            result = file_write.run(
                file_path=str(test_file),
                content="Test content",
                agent=mock_agent,
                tool_call_id="test-tool-call-id",
            )
            assert "ERROR" not in result
            assert test_file.exists()

        finally:
            if test_file.exists():
                test_file.unlink()
            try:
                (Path.cwd() / ".test_tmp" / "subdir" / "nested").rmdir()
                (Path.cwd() / ".test_tmp" / "subdir").rmdir()
                (Path.cwd() / ".test_tmp").rmdir()
            except OSError:
                pass

    def test_file_read_with_offset_limit(self, temp_dir):
        """Test file_read with offset and limit."""
        from pathlib import Path
        from tools import file_read, file_write

        # Use a path within cwd to avoid sandbox rejection
        test_file = Path.cwd() / ".test_tmp" / "test.txt"

        try:
            # Write multi-line content
            content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
            mock_agent = Mock()
            mock_agent.log_file = None
            mock_agent.audit_file = None
            mock_agent.context_file = None
            mock_agent.max_context_tokens = 100000
            mock_agent._sandbox_last_call = None

            file_write.run(
                file_path=str(test_file),
                content=content,
                agent=mock_agent,
                tool_call_id="test-tool-call-id",
            )

            # Read with offset and limit
            result = file_read.run(
                file_path=str(test_file),
                offset=2,
                limit=2,
                agent=mock_agent,
                tool_call_id="test-tool-call-id-2",
            )
            assert "Line 2" in result
            assert "Line 3" in result
            assert "Line 1" not in result
            assert "Line 4" not in result

        finally:
            if test_file.exists():
                test_file.unlink()
            try:
                (Path.cwd() / ".test_tmp").rmdir()
            except OSError:
                pass

    def test_file_read_nonexistent_file(self, temp_dir):
        """Test file_read with nonexistent file."""
        from pathlib import Path
        from tools import file_read

        mock_agent = Mock()
        mock_agent.log_file = None
        mock_agent.audit_file = None
        mock_agent.context_file = None
        mock_agent.max_context_tokens = 100000
        mock_agent._sandbox_last_call = None

        result = file_read.run(
            file_path=str(Path.cwd() / ".test_tmp" / "nonexistent.txt"),
            offset=1,
            limit=10,
            agent=mock_agent,
            tool_call_id="test-tool-call-id",
        )
        assert "ERROR" in result or "not found" in result.lower()


class TestToolNamesUnique:
    """Test that all tool names are unique."""

    def test_no_duplicate_names(self):
        """Verify no duplicate tool names."""
        tools = get_all_tools()
        tool_names = [tool["name"] for tool in tools]
        unique_names = set(tool_names)
        assert len(unique_names) == len(
            tool_names
        ), f"Duplicate tool names found: {[n for n in tool_names if tool_names.count(n) > 1]}"


class TestToolDescriptions:
    """Test that all tools have meaningful descriptions."""

    def test_descriptions_not_empty(self):
        """Verify all tool descriptions are non-empty."""
        tools = get_all_tools()
        for tool in tools:
            assert (
                tool["description"] is not None
            ), f"Tool {tool['name']} missing description"
            assert isinstance(
                tool["description"], str
            ), f"Tool {tool['name']} description must be string"
            assert (
                len(tool["description"]) > 0
            ), f"Tool {tool['name']} description cannot be empty"

    def test_descriptions_meaningful(self):
        """Verify descriptions are at least somewhat meaningful."""
        tools = get_all_tools()
        for tool in tools:
            desc = tool["description"].strip()
            assert (
                len(desc) >= 10
            ), f"Tool {tool['name']} description too short: '{desc}'"
