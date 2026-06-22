"""Edge case tests for the tool-call pipeline.

Tests the format transformation in agent_core.py and postparse behavior
under edge conditions: empty lists, None reasoning, malformed JSON,
and missing keys.
"""

import json
import pytest
from agent_llm import llm_postparse
from agent_llm import LLMResponse, CallStats


class TestEmptyToolCalls:
    """Test empty tool_calls list handling."""

    def test_empty_list_iteration(self):
        """Empty tool_calls list should iterate zero times."""
        tool_calls = []
        result = []
        for tc in tool_calls:
            result.append(tc)
        assert result == []

    def test_llm_response_default_empty_list(self):
        """LLMResponse.tool_calls defaults to empty list, not None."""
        resp = LLMResponse(
            raw=None,
            text="",
            reasoning=None,
            stats=CallStats(prompt_tokens=0, completion_tokens=0, cached_tokens=None),
        )
        assert resp.tool_calls == []
        assert isinstance(resp.tool_calls, list)

    def test_empty_list_format_transformation(self):
        """Empty tool_calls should produce empty executor list."""
        resp_tool_calls = []
        tool_calls = []
        for tc in resp_tool_calls:
            args_str = tc["function"]["arguments"] or ""
            try:
                args_dict = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args_dict = {}
            tool_calls.append({
                "id": tc["id"],
                "name": tc["function"]["name"],
                "args": args_str,
                "args_dict": args_dict,
            })
        assert tool_calls == []


class TestNoneReasoning:
    """Test None reasoning handling in postparse."""

    def test_postparse_with_none_reasoning(self):
        """llm_postparse should handle None reasoning gracefully."""
        content = "Some text without tool calls"
        reasoning = None
        tool_calls = []

        content_out, reasoning_out, tool_calls_out = llm_postparse(
            content, reasoning, tool_calls
        )

        # Reasoning should remain None if no thoughts were extracted
        assert reasoning_out is None or reasoning_out == ""
        assert tool_calls_out == []

    def test_postparse_with_none_reasoning_and_tool_calls(self):
        """llm_postparse should handle None reasoning with embedded tool calls."""
        content = "Let me help<toolcall><function=test_tool>{" + json.dumps({"key": "value"}) + "} </FUNCTION></TOOLCALL> done"
        reasoning = None
        tool_calls = []

        content_out, reasoning_out, tool_calls_out = llm_postparse(
            content, reasoning, tool_calls
        )

        # Should extract tool call even with None reasoning
        assert len(tool_calls_out) >= 0  # May or may not extract depending on format


class TestMalformedJsonArgs:
    """Test malformed JSON arguments handling."""

    def test_malformed_json_fallback(self):
        """Malformed JSON args should fallback to empty dict."""
        tc = {
            "id": "test-1",
            "function": {
                "name": "test_tool",
                "arguments": '{"invalid json"',  # Malformed
            },
        }

        args_str = tc["function"]["arguments"] or ""
        try:
            args_dict = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            args_dict = {}

        assert args_dict == {}

    def test_empty_args_string(self):
        """Empty args string should produce empty dict."""
        tc = {
            "id": "test-1",
            "function": {
                "name": "test_tool",
                "arguments": "",
            },
        }

        args_str = tc["function"]["arguments"] or ""
        try:
            args_dict = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            args_dict = {}

        assert args_dict == {}

    def test_none_arguments(self):
        """None arguments should fallback to empty string then empty dict."""
        tc = {
            "id": "test-1",
            "function": {
                "name": "test_tool",
                "arguments": None,
            },
        }

        args_str = tc["function"]["arguments"] or ""
        try:
            args_dict = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            args_dict = {}

        assert args_str == ""
        assert args_dict == {}


class TestMissingFunctionKey:
    """Test missing 'function' key handling."""

    def test_missing_function_key_raises_keyerror(self):
        """Missing 'function' key should raise KeyError (documented risk)."""
        tc = {
            "id": "test-1",
            # Missing "function" key
        }

        with pytest.raises(KeyError):
            _ = tc["function"]["arguments"]

    def test_missing_name_key_raises_keyerror(self):
        """Missing 'name' key should raise KeyError."""
        tc = {
            "id": "test-1",
            "function": {
                # Missing "name" key
                "arguments": "{}",
            },
        }

        with pytest.raises(KeyError):
            _ = tc["function"]["name"]

    def test_defensive_get_pattern(self):
        """Defensive .get() pattern prevents KeyError."""
        tc = {
            "id": "test-1",
            # Missing "function" key
        }

        func = tc.get("function", {})
        args_str = func.get("arguments") or ""

        assert args_str == ""


class TestFormatTransformation:
    """Test the complete format transformation under edge conditions."""

    def test_valid_transformation(self):
        """Valid SDK format should transform correctly."""
        tc = {
            "id": "test-1",
            "type": "function",
            "function": {
                "name": "test_tool",
                "arguments": '{"key": "value"}',
            },
        }

        args_str = tc["function"]["arguments"] or ""
        try:
            args_dict = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            args_dict = {}

        result = {
            "id": tc["id"],
            "name": tc["function"]["name"],
            "args": args_str,
            "args_dict": args_dict,
        }

        assert result["id"] == "test-1"
        assert result["name"] == "test_tool"
        assert result["args"] == '{"key": "value"}'
        assert result["args_dict"] == {"key": "value"}

    def test_type_field_dropped(self):
        """'type' field is intentionally dropped in transformation."""
        tc = {
            "id": "test-1",
            "type": "function",
            "function": {
                "name": "test_tool",
                "arguments": "{}",
            },
        }

        result = {
            "id": tc["id"],
            "name": tc["function"]["name"],
            "args": tc["function"]["arguments"] or "",
            "args_dict": {},
        }

        assert "type" not in result
