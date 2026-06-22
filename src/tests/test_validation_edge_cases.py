"""Unit tests for tool argument validation improvements.

Tests cover edge cases for:
- _validate_tool_args (unknown fields, missing required, backward compat)
- _generate_validation_error (unknown, missing, both, type hints)
- _validate_args_structure (None, non-dict, valid)
- _get_tool_schema_info (valid tool, missing Args, missing globals)
"""

import pytest
from tools.validation import (
    _validate_tool_args,
    _generate_validation_error,
    _get_tool_schema_info,
)
from agent_tool_executor import _validate_args_structure


class TestValidateToolArgs:
    """Test _validate_tool_args edge cases."""

    def test_empty_args_no_required(self):
        """Empty args with no required fields should be valid."""
        is_valid, unknown, missing = _validate_tool_args({}, [])
        assert is_valid
        assert unknown == []
        assert missing == []

    def test_empty_args_with_required(self):
        """Empty args with required fields should fail."""
        is_valid, unknown, missing = _validate_tool_args({}, ["cmd"], ["cmd"])
        assert not is_valid
        assert unknown == []
        assert missing == ["cmd"]

    def test_unknown_fields_only(self):
        """Unknown fields should be detected."""
        is_valid, unknown, missing = _validate_tool_args({"bad": 1}, ["good"])
        assert not is_valid
        assert unknown == ["bad"]
        assert missing == []

    def test_missing_fields_only(self):
        """Missing required fields should be detected."""
        is_valid, unknown, missing = _validate_tool_args({"good": 1}, ["good", "required"], ["required"])
        assert not is_valid
        assert unknown == []
        assert missing == ["required"]

    def test_both_unknown_and_missing(self):
        """Both unknown and missing should be detected."""
        is_valid, unknown, missing = _validate_tool_args(
            {"bad": 1}, ["good", "required"], ["required"]
        )
        assert not is_valid
        assert unknown == ["bad"]
        assert missing == ["required"]

    def test_all_valid_args(self):
        """All valid args should pass."""
        is_valid, unknown, missing = _validate_tool_args(
            {"good": 1, "required": 2}, ["good", "required"], ["required"]
        )
        assert is_valid
        assert unknown == []
        assert missing == []

    def test_backward_compat_no_required(self):
        """Calling with 2 args (no required_fields) should work like before."""
        is_valid, unknown, missing = _validate_tool_args({"bad": 1}, ["good"])
        assert not is_valid
        assert unknown == ["bad"]
        assert missing == []  # No required check when not provided

    def test_backward_compat_valid(self):
        """Valid args with backward compat call should pass."""
        is_valid, unknown, missing = _validate_tool_args({"good": 1}, ["good"])
        assert is_valid
        assert unknown == []
        assert missing == []

    def test_multiple_missing(self):
        """Multiple missing required fields should all be reported."""
        is_valid, unknown, missing = _validate_tool_args(
            {}, ["a", "b", "c"], ["a", "b", "c"]
        )
        assert not is_valid
        assert unknown == []
        assert missing == ["a", "b", "c"]

    def test_partial_missing(self):
        """Some required present, some missing."""
        is_valid, unknown, missing = _validate_tool_args(
            {"a": 1}, ["a", "b", "c"], ["a", "b", "c"]
        )
        assert not is_valid
        assert unknown == []
        assert missing == ["b", "c"]


class TestGenerateValidationError:
    """Test _generate_validation_error edge cases."""

    def test_only_unknown_fields(self):
        """Error with only unknown fields."""
        error = _generate_validation_error(
            "test_tool", ["bad"], ["good", "required"]
        )
        assert "Unknown parameters" in error
        assert "'bad'" in error
        assert "Valid parameters" in error

    def test_only_missing_fields(self):
        """Error with only missing fields."""
        error = _generate_validation_error(
            "test_tool", [], ["good", "required"],
            missing_fields=["required"],
            field_types={"good": "string", "required": "integer"},
        )
        assert "Missing required" in error
        assert "'required'" in error

    def test_both_unknown_and_missing(self):
        """Error with both unknown and missing fields."""
        error = _generate_validation_error(
            "test_tool", ["bad"], ["good", "required"],
            missing_fields=["required"],
            field_types={"good": "string", "required": "integer"},
        )
        assert "Unknown parameters" in error
        assert "Missing required" in error
        assert "'bad'" in error
        assert "'required'" in error

    def test_with_type_hints(self):
        """Error includes type hints for missing fields."""
        error = _generate_validation_error(
            "test_tool", [], ["required"],
            missing_fields=["required"],
            field_types={"required": "integer"},
        )
        assert "integer" in error

    def test_empty_valid_fields(self):
        """Error with empty valid_fields list."""
        error = _generate_validation_error(
            "test_tool", ["bad"], []
        )
        assert "Unknown parameters" in error
        assert "'bad'" in error

    def test_fuzzy_suggestions(self):
        """Fuzzy suggestions for unknown fields."""
        error = _generate_validation_error(
            "test_tool", ["path"], ["file_path", "timeout"]
        )
        assert "Did you mean" in error

    def test_no_suggestions_for_obscure_unknown(self):
        """No suggestions when no close match exists."""
        error = _generate_validation_error(
            "test_tool", ["xyz_nonexistent"], ["file_path", "timeout"]
        )
        # Should still have valid parameters listed
        assert "Valid parameters" in error


class TestValidateArgsStructure:
    """Test _validate_args_structure edge cases."""

    def test_valid_dict_args(self):
        """Valid dict args should produce no issues."""
        issues = _validate_args_structure({"args_dict": {"key": "value"}}, "test_tool")
        assert issues == []

    def test_none_args(self):
        """None args should produce an issue."""
        issues = _validate_args_structure({"args_dict": None}, "test_tool")
        assert len(issues) == 1
        assert "None" in issues[0]

    def test_string_args(self):
        """String args should produce an issue."""
        issues = _validate_args_structure({"args_dict": "bad"}, "test_tool")
        assert len(issues) == 1
        assert "str" in issues[0]

    def test_list_args(self):
        """List args should produce an issue."""
        issues = _validate_args_structure({"args_dict": [1, 2]}, "test_tool")
        assert len(issues) == 1
        assert "list" in issues[0]

    def test_empty_dict_args(self):
        """Empty dict args should be valid (no issues)."""
        issues = _validate_args_structure({"args_dict": {}}, "test_tool")
        assert issues == []

    def test_int_args(self):
        """Integer args should produce an issue."""
        issues = _validate_args_structure({"args_dict": 42}, "test_tool")
        assert len(issues) == 1
        assert "int" in issues[0]

    def test_missing_args_dict_key(self):
        """Missing args_dict key should produce an issue (None)."""
        issues = _validate_args_structure({}, "test_tool")
        assert len(issues) == 1
        assert "None" in issues[0]


class TestGetToolSchemaInfo:
    """Test _get_tool_schema_info edge cases."""

    def test_function_without_globals(self):
        """Function without __globals__ should return empty."""
        # Built-in functions don't have __globals__
        result = _get_tool_schema_info(len)
        assert result == ([], [], {})

    def test_function_without_args(self):
        """Function without Args in globals should return empty."""
        def simple_func(x):
            return x
        result = _get_tool_schema_info(simple_func)
        assert result == ([], [], {})

    def test_lambda(self):
        """Lambda should return empty."""
        result = _get_tool_schema_info(lambda x: x)
        assert result == ([], [], {})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
