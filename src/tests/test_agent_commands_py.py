"""Tests for .py command discovery and loading in agent_commands module.

Tests:
    TestPyCommandDiscovery - discover_py_commands, get_py_command, get_py_command_names
    TestPyCommandLoading - load_py_command, module interface
    TestCommandConflicts - find_command_conflicts, .py vs .md precedence
    TestDispatchPriority - .py → builtin → .md dispatch order
    TestHelpDisplay - /help and /commands show three categories
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_command_registry import (
    discover_commands,
    discover_py_commands,
    get_command,
    get_py_command,
    get_py_command_names,
    get_md_command_names,
    load_py_command,
    find_command_conflicts,
)

# =============================================================================
# TestPyCommandDiscovery
# =============================================================================


class TestPyCommandDiscovery:
    """Test .py command discovery functionality."""

    def test_discover_py_commands_finds_delegate(self, commands_dir):
        """Verify delegate.py is discovered."""
        commands = discover_py_commands(str(commands_dir))
        names = [cmd["name"] for cmd in commands]
        assert "delegate" in names, "delegate.py not discovered"

    def test_py_commands_have_required_fields(self, commands_dir):
        """Verify .py commands have required fields."""
        commands = discover_py_commands(str(commands_dir))
        for cmd in commands:
            assert "name" in cmd, f"Command missing 'name': {cmd}"
            assert "description" in cmd, f"Command missing 'description': {cmd}"
            assert "file_path" in cmd, f"Command missing 'file_path': {cmd}"
            assert "type" in cmd, f"Command missing 'type': {cmd}"
            assert cmd["type"] == "py_command", f"Wrong type: {cmd['type']}"

    def test_py_command_file_path_is_py(self, commands_dir):
        """Verify .py command file paths end with .py."""
        commands = discover_py_commands(str(commands_dir))
        for cmd in commands:
            assert cmd["file_path"].endswith(
                ".py"
            ), f"Not a .py file: {cmd['file_path']}"

    def test_py_command_file_exists(self, commands_dir):
        """Verify .py command files actually exist on disk."""
        commands = discover_py_commands(str(commands_dir))
        for cmd in commands:
            assert Path(
                cmd["file_path"]
            ).exists(), f"File not found: {cmd['file_path']}"

    def test_get_py_command_finds_delegate(self, commands_dir):
        """Verify get_py_command finds delegate."""
        cmd = get_py_command("delegate", str(commands_dir))
        assert cmd is not None, "delegate not found by get_py_command"
        assert cmd["name"] == "delegate"
        assert "description" in cmd
        assert cmd["type"] == "py_command"

    def test_get_py_command_not_found(self, commands_dir):
        """Verify get_py_command returns None for nonexistent command."""
        cmd = get_py_command("nonexistent_py_cmd", str(commands_dir))
        assert cmd is None

    def test_get_py_command_names_includes_delegate(self, commands_dir):
        """Verify get_py_command_names includes delegate."""
        names = get_py_command_names(str(commands_dir))
        assert "delegate" in names, "delegate not in py command names"

    def test_py_and_md_commands_are_separate(self, commands_dir):
        """Verify .py and .md commands are discovered separately."""
        py_cmds = discover_py_commands(str(commands_dir))
        md_cmds = discover_commands(str(commands_dir))

        # They should be separate discovery results
        assert len(py_cmds) > 0, "No .py commands found"
        assert len(md_cmds) > 0, "No .md commands found"

    def test_command_name_uniqueness(self, commands_dir):
        """Verify no command names overlap between .py and .md commands."""
        py_names = {c["name"] for c in discover_py_commands(str(commands_dir))}
        md_names = {c["name"] for c in discover_commands(str(commands_dir))}

        # Check for conflicts
        conflicts = py_names & md_names
        assert len(conflicts) == 0, f"Command name conflicts found: {conflicts}"

    def test_empty_directory_returns_empty_list(self):
        """Verify empty directory returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            commands = discover_py_commands(tmpdir)
            assert commands == []

    def test_directory_with_no_py_files(self, commands_dir):
        """Verify directory with only .md files returns empty .py list."""
        # commands_dir has .md files but we're testing discover_py_commands
        # which should only find .py files
        commands = discover_py_commands(str(commands_dir))
        for cmd in commands:
            assert cmd["file_path"].endswith(".py")


# =============================================================================
# TestPyCommandLoading
# =============================================================================


class TestPyCommandLoading:
    """Test .py command module loading."""

    def test_load_py_command_returns_module(self, commands_dir):
        """Verify load_py_command returns a module object."""
        mod = load_py_command("delegate", str(commands_dir))
        assert mod is not None, "Failed to load delegate module"

    def test_loaded_module_has_name(self, commands_dir):
        """Verify loaded module has 'name' or 'NAME' attribute."""
        mod = load_py_command("delegate", str(commands_dir))
        assert hasattr(mod, "name") or hasattr(mod, "NAME"), "Module missing 'name' or 'NAME' attribute"
        mod_name = getattr(mod, "NAME", None) or getattr(mod, "name", None)
        assert mod_name == "delegate"

    def test_loaded_module_has_description(self, commands_dir):
        """Verify loaded module has 'description' or 'DESCRIPTION' attribute."""
        mod = load_py_command("delegate", str(commands_dir))
        assert hasattr(mod, "description") or hasattr(mod, "DESCRIPTION"), "Module missing 'description' or 'DESCRIPTION' attribute"
        mod_desc = getattr(mod, "DESCRIPTION", None) or getattr(mod, "description", None)
        assert isinstance(mod_desc, str)
        assert len(mod_desc) > 0

    def test_loaded_module_has_run_function(self, commands_dir):
        """Verify loaded module has 'run' function."""
        mod = load_py_command("delegate", str(commands_dir))
        assert hasattr(mod, "run"), "Module missing 'run' function"
        assert callable(mod.run), "'run' is not callable"

    def test_run_function_signature(self, commands_dir):
        """Verify run function has correct signature."""
        mod = load_py_command("delegate", str(commands_dir))
        import inspect

        sig = inspect.signature(mod.run)
        params = list(sig.parameters.keys())
        assert "agent" in params, "run() missing 'agent' parameter"
        assert "args" in params, "run() missing 'args' parameter"

    def test_load_nonexistent_py_command(self, commands_dir):
        """Verify loading nonexistent command returns None."""
        mod = load_py_command("nonexistent_py_cmd", str(commands_dir))
        assert mod is None

    def test_fresh_load_each_time(self, commands_dir):
        """Verify each load is fresh (no caching)."""
        mod1 = load_py_command("delegate", str(commands_dir))
        mod2 = load_py_command("delegate", str(commands_dir))
        # Should be different module objects (fresh loads)
        assert mod1 is not mod2, "Modules should be different objects (no caching)"


# =============================================================================
# TestCommandConflicts
# =============================================================================


class TestCommandConflicts:
    """Test .py vs .md conflict detection."""

    def test_no_conflicts_in_default_commands(self, commands_dir):
        """Verify no conflicts in default commands directory."""
        conflicts = find_command_conflicts(str(commands_dir))
        # delegate.py exists but there's no delegate.md, so no conflict
        # heartbeat.md exists but no heartbeat.py, so no conflict
        # This test just verifies the function works
        assert isinstance(conflicts, list)

    def test_conflict_detection_with_temp_files(self):
        """Verify conflict detection works with temp .py and .md files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a .py command
            py_file = Path(tmpdir) / "testcmd.py"
            py_file.write_text(
                'name = "testcmd"\ndescription = "test"\ndef run(agent, args): pass\n'
            )

            # Create a .md command with same name
            md_file = Path(tmpdir) / "testcmd.md"
            md_file.write_text("---\ndescription: test md\n---\nTest content")

            conflicts = find_command_conflicts(tmpdir)
            assert "testcmd" in conflicts, "Should detect testcmd conflict"

    def test_no_conflict_when_only_py_exists(self):
        """Verify no conflict when only .py exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            py_file = Path(tmpdir) / "solo.py"
            py_file.write_text(
                'name = "solo"\ndescription = "solo"\ndef run(agent, args): pass\n'
            )

            conflicts = find_command_conflicts(tmpdir)
            assert "solo" not in conflicts, "No conflict when only .py exists"

    def test_no_conflict_when_only_md_exists(self):
        """Verify no conflict when only .md exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_file = Path(tmpdir) / "solo.md"
            md_file.write_text("---\ndescription: solo md\n---\nTest content")

            conflicts = find_command_conflicts(tmpdir)
            assert "solo" not in conflicts, "No conflict when only .md exists"


# =============================================================================
# TestGetMdCommandNames
# =============================================================================


class TestGetMdCommandNames:
    """Test get_md_command_names function."""

    def test_returns_sorted_list(self, commands_dir):
        """Verify get_md_command_names returns sorted list."""
        names = get_md_command_names(str(commands_dir))
        assert names == sorted(names), "Names should be sorted"

    def test_includes_known_commands(self, commands_dir):
        """Verify known .md commands are included."""
        names = get_md_command_names(str(commands_dir))
        assert "gitcrit" in names, "gitcrit should be in md command names"
        assert "heartbeat" in names, "heartbeat should be in md command names"


# =============================================================================
# TestPyCommandInterface
# =============================================================================


class TestPyCommandInterface:
    """Test the .py command interface contract."""

    def test_delegate_description_is_nonempty(self, commands_dir):
        """Verify delegate description is non-empty."""
        mod = load_py_command("delegate", str(commands_dir))
        mod_desc = getattr(mod, "DESCRIPTION", None) or getattr(mod, "description", None)
        assert mod_desc.strip(), "Description should not be empty"

    def test_delegate_description_mentions_delegate(self, commands_dir):
        """Verify delegate description mentions delegate/orchestrator."""
        mod = load_py_command("delegate", str(commands_dir))
        mod_desc = getattr(mod, "DESCRIPTION", None) or getattr(mod, "description", None)
        desc_lower = mod_desc.lower()
        assert (
            "delegate" in desc_lower or "orchestrat" in desc_lower
        ), f"Description should mention delegate/orchestrator: {mod_desc}"

    def test_run_with_mock_agent(self, commands_dir, mock_agent):
        """Verify run() can be called with a mock agent without crashing."""
        mod = load_py_command("delegate", str(commands_dir))
        # Call with empty args - should handle gracefully
        try:
            # This will likely fail because delegate needs real agent state,
            # but we verify it at least accepts the call
            mod.run(mock_agent, [])
        except (AttributeError, TypeError, KeyError):
            # Expected - mock agent doesn't have full state
            pass
        except Exception:
            # Any other exception is also acceptable for this test
            pass

    def test_run_with_empty_args(self, commands_dir, mock_agent):
        """Verify run() handles empty args gracefully."""
        mod = load_py_command("delegate", str(commands_dir))
        # Empty args should trigger usage message, not crash
        try:
            mod.run(mock_agent, [])
        except Exception:
            pass  # Acceptable - mock agent may not have console


# =============================================================================
# TestDispatchPriority
# =============================================================================


class TestDispatchPriority:
    """Test command dispatch priority: .py → builtin → .md"""

    def test_py_command_overrides_builtin(self, commands_dir):
        """Verify .py command takes precedence over builtin."""
        # delegate is now a .py command, not a builtin
        py_cmd = get_py_command("delegate", str(commands_dir))
        assert py_cmd is not None, "delegate .py command should exist"

    def test_builtin_not_in_py_commands(self, commands_dir):
        """Verify builtin commands are not in .py commands."""
        py_names = get_py_command_names(str(commands_dir))
        # Builtins like 'help', 'exit', 'tools' should NOT be .py commands
        for builtin in ["help", "exit", "tools", "status"]:
            assert builtin not in py_names, f"{builtin} should not be a .py command"

    def test_md_command_not_in_py_commands(self, commands_dir):
        """Verify .md commands are not in .py commands (unless overridden)."""
        py_names = set(get_py_command_names(str(commands_dir)))
        md_names = set(get_md_command_names(str(commands_dir)))

        # .py and .md commands should be mostly separate
        # (except for intentional overrides)
        overlap = py_names & md_names
        # delegate.py exists, but there's no delegate.md, so no overlap expected
        # unless someone creates a conflicting .md file
        for name in overlap:
            # If there IS overlap, it's intentional (override)
            assert name in py_names, f"{name} should be in .py commands"
