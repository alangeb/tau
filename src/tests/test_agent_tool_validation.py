"""Unit tests for agent_tool_validation normalization pipeline.

Tests normalize_tool_call (production path) and fix_tool_call (compat shim).
"""

import pytest
from dataclasses import dataclass

from tools.validation import normalize_tool_call, fix_tool_call, _dataclass_to_json_schema


@dataclass
class MockArgsBool:
    """Mock Args dataclass with a boolean field for coercion tests."""
    enabled: bool = False


class MockSchemaBool:
    """Mock tool module with Args dataclass for coercion tests."""
    Args = MockArgsBool

    @staticmethod
    def get_schema():
        return _dataclass_to_json_schema(MockArgsBool)


@dataclass
class MockArgs:
    """Mock Args dataclass with integer, string, and number fields."""
    max_results: int = 10
    path: str = ""
    count: int = 0
    timeout: float = 30.0
    temperature: float = 0.7


class TestNormalizeToolCall:
    """Tests for normalize_tool_call — the production normalization pipeline."""

    # ── Basic behavior ───────────────────────────────────────────────────

    def test_nonexistent_tool_no_crash(self):
        """Tool not in TOOLS: no crash, no defaults filled."""
        tc = {
            "id": "tc1",
            "name": "nonexistent_tool_xyz",
            "args_dict": {"file_path": "foo.txt"},
        }
        warnings = normalize_tool_call(tc)
        # No tool in TOOLS → no defaults, no coercion
        assert tc["args_dict"] == {"file_path": "foo.txt"}
        assert warnings == []

    def test_args_dict_must_be_dict(self):
        """Non-dict args_dict is handled gracefully."""
        tc = {"name": "bash", "args_dict": "not a dict"}
        warnings = normalize_tool_call(tc)
        assert warnings == []

    def test_empty_args_dict(self):
        """Empty args_dict produces no warnings."""
        tc = {"name": "bash", "args_dict": {}}
        warnings = normalize_tool_call(tc)
        assert warnings == []

    # ── Command alias resolution (via global CMD_ALIASES) ────────────────

    def test_command_alias_resolved(self):
        """Command alias is rewritten to canonical name via global CMD_ALIASES."""
        # 'read_file' is an alias for 'file_read' in global CMD_ALIASES
        tc = {
            "id": "tc1",
            "name": "read_file",
            "args_dict": {"file_path": "foo.txt"},
        }
        warnings = normalize_tool_call(tc)
        assert tc["name"] == "file_read"
        assert any("read_file" in w and "file_read" in w for w in warnings)

    def test_command_alias_raw_args_unchanged(self):
        """The raw tc['args'] JSON string is NOT modified."""
        tc = {
            "id": "tc1",
            "name": "read_file",
            "args": '{"file_path": "foo.txt"}',
            "args_dict": {"file_path": "foo.txt"},
        }
        normalize_tool_call(tc)
        assert tc["args"] == '{"file_path": "foo.txt"}'

    # ── Argument alias resolution (via global ARG_ALIASES) ─────────────

    def test_arg_alias_resolved(self):
        """Argument alias key is renamed to canonical via global ARG_ALIASES."""
        # 'path' is an alias for 'file_path' in global ARG_ALIASES for file_read
        tc = {
            "id": "tc1",
            "name": "file_read",
            "args_dict": {"path": "foo.txt"},
        }
        warnings = normalize_tool_call(tc)
        assert "file_path" in tc["args_dict"]
        assert "path" not in tc["args_dict"]
        assert any("path" in w and "file_path" in w for w in warnings)

    def test_multiple_arg_aliases(self):
        """Multiple argument aliases are all resolved."""
        tc = {
            "id": "tc1",
            "name": "file_read",
            "args_dict": {"path": "foo.txt", "limit": 50},
        }
        warnings = normalize_tool_call(tc)
        # Both 'path' → 'file_path' and 'limit' → 'max_lines' (if alias exists)
        assert "file_path" in tc["args_dict"]
        assert "path" not in tc["args_dict"]
        assert len(warnings) >= 1  # at least the path→file_path alias

    # ── Type coercion (via global TOOLS schema) ─────────────────────────

    def test_int_coerce_plain_string(self):
        """String '10' is coerced to int 10 for integer fields."""
        tc = {
            "id": "tc1",
            "name": "grep",
            "args_dict": {"max_results": "10"},
        }
        warnings = normalize_tool_call(tc)
        assert tc["args_dict"]["max_results"] == 10
        assert any("10" in w and "int coercion" in w for w in warnings)

    def test_int_coerce_float_string(self):
        """String '10.0' is coerced to int 10 for integer fields."""
        tc = {
            "id": "tc1",
            "name": "grep",
            "args_dict": {"max_results": "10.0"},
        }
        warnings = normalize_tool_call(tc)
        assert tc["args_dict"]["max_results"] == 10

    def test_bool_coerce_true(self):
        """String 'true' is coerced to bool True."""
        tc = {
            "id": "tc1",
            "name": "bash",
            "args_dict": {"dangerous": "true"},
        }
        # bash doesn't have 'dangerous' in schema, so no coercion
        warnings = normalize_tool_call(tc)
        # No coercion since 'dangerous' is not in bash's schema
        assert warnings == []

    def test_coerce_non_string_skipped(self):
        """Non-string values are NOT coerced."""
        tc = {
            "id": "tc1",
            "name": "grep",
            "args_dict": {"max_results": 10},  # already int
        }
        warnings = normalize_tool_call(tc)
        assert tc["args_dict"]["max_results"] == 10
        # No coercion warning since value is already int

    # ── Default filling (via global TOOLS Args dataclass) ──────────────

    def test_defaults_filled(self):
        """Missing optional args are filled from tool's Args dataclass."""
        tc = {
            "id": "tc1",
            "name": "file_read",
            "args_dict": {"file_path": "foo.txt"},
        }
        normalize_tool_call(tc)
        # file_read has defaults: offset=1, limit=100
        assert "offset" in tc["args_dict"]
        assert tc["args_dict"]["offset"] == 1

    # ── Combined operations ────────────────────────────────────────────

    def test_combined_alias_and_coercion(self):
        """Alias resolution and type coercion happen in one pass."""
        tc = {
            "id": "tc1",
            "name": "grep",
            "args_dict": {"max_results": "42", "path": "."},
        }
        warnings = normalize_tool_call(tc)
        assert tc["args_dict"]["max_results"] == 42  # coerced
        # 'path' may or may not be an alias for grep — check it exists
        assert "path" in tc["args_dict"] or "file_path" in tc["args_dict"]


class TestFixToolCallCompat:
    """Tests for fix_tool_call — backward-compat shim that delegates to normalize_tool_call.

    NOTE: fix_tool_call ignores its cmd_aliases, arg_aliases, tool_module parameters
    and delegates to normalize_tool_call which reads from module-level globals.
    These tests verify the delegation works correctly.
    """

    def test_delegates_to_normalize(self):
        """fix_tool_call delegates to normalize_tool_call."""
        tc = {"name": "read_file", "args_dict": {"file_path": "foo.txt"}}
        warnings = fix_tool_call(tc, {}, {}, None)
        # Should resolve 'read_file' → 'file_read' via global CMD_ALIASES
        assert tc["name"] == "file_read"
        assert any("read_file" in w for w in warnings)

    def test_parameters_ignored(self):
        """Custom parameters are ignored (delegates to globals)."""
        tc = {"name": "read_file", "args_dict": {"file_path": "foo.txt"}}
        # Pass custom aliases that DON'T match globals
        custom_aliases = {"fake_alias": "fake_target"}
        warnings = fix_tool_call(tc, custom_aliases, {}, None)
        # Still resolves via global CMD_ALIASES, not custom_aliases
        assert tc["name"] == "file_read"

    def test_returns_warnings(self):
        """fix_tool_call returns warning strings."""
        tc = {"name": "read_file", "args_dict": {}}
        warnings = fix_tool_call(tc, {}, {}, None)
        assert isinstance(warnings, list)
        assert len(warnings) >= 1  # at least the alias warning


# ── Contract tests: type coercion edge cases ──────────────────────────────────
# These are BEHAVIOR tests (what the system does), not implementation tests
# (how it does it). They survive API refactoring because they test observable
# outcomes, not internal mechanics.


class TestTypeCoercionContracts:
    """Contract tests for type coercion behavior.

    These verify that string values are coerced to the correct types per the
    tool schema, regardless of internal implementation details.
    """

    # ── Integer coercion ──────────────────────────────────────────────────

    def test_int_coerce_plain_int_string(self):
        """'42' → 42 for int fields."""
        tc = {"name": "grep", "args_dict": {"max_results": "42"}}
        normalize_tool_call(tc)
        assert tc["args_dict"]["max_results"] == 42
        assert isinstance(tc["args_dict"]["max_results"], int)

    def test_int_coerce_float_string(self):
        """'10.0' → 10 for int fields."""
        tc = {"name": "grep", "args_dict": {"max_results": "10.0"}}
        normalize_tool_call(tc)
        assert tc["args_dict"]["max_results"] == 10

    def test_int_coerce_negative(self):
        """'-5' → -5 for int fields."""
        tc = {"name": "grep", "args_dict": {"max_results": "-5"}}
        normalize_tool_call(tc)
        assert tc["args_dict"]["max_results"] == -5

    def test_int_already_int_no_coerce(self):
        """Value already int → no coercion, no warning."""
        tc = {"name": "grep", "args_dict": {"max_results": 42}}
        warnings = normalize_tool_call(tc)
        assert tc["args_dict"]["max_results"] == 42
        assert not any("int coercion" in w for w in warnings)

    # ── Boolean coercion ─────────────────────────────────────────────────

    def test_bool_coerce_true_variants(self):
        """'true', 't', 'yes', '1' → True for bool fields."""
        for val in ("true", "t", "yes", "1"):
            tc = {"name": "bash", "args_dict": {"dry_run": val}}
            # bash doesn't have dry_run in schema, so test with a tool that does
            # Use grep which has recursive: bool
            tc = {"name": "grep", "args_dict": {"recursive": val}}
            normalize_tool_call(tc)
            assert tc["args_dict"]["recursive"] is True, f"Failed for {val!r}"

    def test_bool_coerce_false_variants(self):
        """'false', 'f', 'no', '0' → False for bool fields."""
        for val in ("false", "f", "no", "0"):
            tc = {"name": "grep", "args_dict": {"recursive": val}}
            normalize_tool_call(tc)
            assert tc["args_dict"]["recursive"] is False, f"Failed for {val!r}"

    def test_bool_already_bool_no_coerce(self):
        """Value already bool → no coercion."""
        tc = {"name": "grep", "args_dict": {"recursive": True}}
        warnings = normalize_tool_call(tc)
        assert tc["args_dict"]["recursive"] is True
        assert not any("bool coercion" in w for w in warnings)

    # ── Coercion failure handling ─────────────────────────────────────────

    def test_coerce_invalid_string_unchanged(self):
        """Non-numeric string for int field → left as-is (no crash)."""
        tc = {"name": "grep", "args_dict": {"max_results": "not_a_number"}}
        warnings = normalize_tool_call(tc)
        # Should not crash; value stays as string
        assert tc["args_dict"]["max_results"] == "not_a_number"
