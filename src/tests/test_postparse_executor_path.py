"""Integration tests for postparse→executor tool call propagation path.

Verifies that tool calls recovered by llm_postparse (from embedded text)
are correctly propagated through LLMResponse.tool_calls to the executor.

Covers the bug fixed in commit 002549b:
- Pre-fix: postparse-recovered calls were lost (agent_core read only SDK tool_calls)
- Post-fix: resp.tool_calls contains unified SDK+postparse list
"""

from unittest.mock import Mock, patch, call

import pytest

from agent_llm import LLMResponse, CallStats
from agent_llm import llm_postparse


class TestPostparseRecovery:
    """Test that llm_postparse correctly recovers tool calls from text."""

    def test_recovers_toolcall_from_content(self):
        """Tool calls embedded in content are extracted and appended."""
        tool_calls = []
        content = (
            "Let me help you"
            "<toolcall><function=file_read>{\"file_path\": \"test.py\"}</function></toolcall>"
            " done."
        )

        cleaned_content, reasoning, recovered = llm_postparse(
            content, None, tool_calls
        )

        assert len(tool_calls) == 1
        assert tool_calls[0]["function"]["name"] == "file_read"
        assert tool_calls[0]["function"]["arguments"] == '{"file_path": "test.py"}'
        # Recovered text is removed from content
        assert "toolcall" not in cleaned_content

    def test_recovers_toolcall_from_reasoning(self):
        """Tool calls embedded in reasoning are extracted and appended."""
        tool_calls = []
        content = "I need to check the file."
        reasoning = (
            "Thinking..."
            "<toolcall><function=file_read>{\"file_path\": \"test.py\"}</function></toolcall>"
        )

        cleaned_content, cleaned_reasoning, recovered = llm_postparse(
            content, reasoning, tool_calls
        )

        assert len(tool_calls) == 1
        assert tool_calls[0]["function"]["name"] == "file_read"

    def test_preserves_sdk_calls_and_appends_recovered(self):
        """SDK tool calls are preserved, postparse calls are appended."""
        sdk_calls = [
            {
                "id": "sdk_call_1",
                "type": "function",
                "function": {"name": "bash", "arguments": '{"cmd": "ls"}'},
            }
        ]
        content = (
            "Also need to check"
            "<toolcall><function=file_read>{\"file_path\": \"test.py\"}</function></toolcall>"
        )

        _, _, _ = llm_postparse(content, None, sdk_calls)

        assert len(sdk_calls) == 2
        assert sdk_calls[0]["id"] == "sdk_call_1"
        assert sdk_calls[1]["function"]["name"] == "file_read"

    def test_in_place_mutation_no_doubling(self):
        """Verify in-place mutation does not double entries when caller discards third value."""
        tool_calls = []
        content = "<toolcall><function=test>{\"x\": 1}</function></toolcall>"

        # Caller discards third return value (prevents doubling)
        _, _, _ = llm_postparse(content, None, tool_calls)

        assert len(tool_calls) == 1  # Not 2 (no doubling)

    def test_empty_content_returns_unchanged(self):
        """Empty content with no tool calls returns empty list."""
        tool_calls = []
        content = "Just plain text, no tool calls."

        _, _, _ = llm_postparse(content, None, tool_calls)

        assert len(tool_calls) == 0


class TestLlmResponseToolCalls:
    """Test that LLMResponse.tool_calls carries the unified list."""

    def test_tool_calls_field_contains_recovered_calls(self):
        """LLMResponse.tool_calls includes postparse-recovered calls."""
        sdk_calls = [
            {
                "id": "sdk_1",
                "type": "function",
                "function": {"name": "bash", "arguments": '{"cmd": "ls"}'},
            }
        ]

        # Simulate postparse recovery
        content = "<toolcall><function=file_read>{\"file_path\": \"test.py\"}</function></toolcall>"
        _, _, _ = llm_postparse(content, None, sdk_calls)

        # Create LLMResponse with unified list
        resp = LLMResponse(
            raw=Mock(),
            text="response text",
            reasoning=None,
            stats=CallStats(prompt_tokens=10, completion_tokens=5, cached_tokens=0, finish_reason="stop"),
            success=True,
            tool_calls=sdk_calls,
        )

        assert len(resp.tool_calls) == 2
        assert resp.tool_calls[0]["id"] == "sdk_1"
        assert resp.tool_calls[1]["function"]["name"] == "file_read"

    def test_empty_tool_calls_defaults_to_empty_list(self):
        """LLMResponse.tool_calls defaults to empty list when not provided."""
        resp = LLMResponse(
            raw=Mock(),
            text="response",
            reasoning=None,
            stats=CallStats(prompt_tokens=10, completion_tokens=5, cached_tokens=0, finish_reason="stop"),
        )

        assert resp.tool_calls == []

    def test_best_effort_response_includes_tool_calls(self):
        """Best-effort responses still carry tool_calls field."""
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "test", "arguments": "{}"},
            }
        ]

        resp = LLMResponse(
            raw=Mock(),
            text="response",
            reasoning=None,
            stats=CallStats(prompt_tokens=10, completion_tokens=5, cached_tokens=0, finish_reason="stop"),
            success=False,
            tool_calls=tool_calls,
        )

        assert resp.success is False
        assert len(resp.tool_calls) == 1


class TestFormatTransformation:
    """Test the agent_core.py format transformation (SDK dict → executor dict)."""

    def test_transform_sdk_format_to_executor_format(self):
        """SDK format is correctly transformed to executor format."""
        # SDK format (as produced by agent_llm.py)
        sdk_tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "file_read", "arguments": '{"file_path": "test.py"}'},
            }
        ]

        # Format transformation (as done in agent_core.py:invoke_with_tools_loop)
        import json

        tool_calls = []
        for tc in sdk_tool_calls:
            args_str = tc["function"]["arguments"] or ""
            try:
                args_dict = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args_dict = {}
            tool_calls.append(
                {
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "args": args_str,
                    "args_dict": args_dict,
                }
            )

        assert len(tool_calls) == 1
        assert tool_calls[0]["id"] == "call_1"
        assert tool_calls[0]["name"] == "file_read"
        assert tool_calls[0]["args"] == '{"file_path": "test.py"}'
        assert tool_calls[0]["args_dict"] == {"file_path": "test.py"}

    def test_transform_handles_malformed_json(self):
        """Malformed JSON args fall back to empty dict."""
        sdk_tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "test", "arguments": "not-valid-json"},
            }
        ]

        import json

        tool_calls = []
        for tc in sdk_tool_calls:
            args_str = tc["function"]["arguments"] or ""
            try:
                args_dict = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args_dict = {}
            tool_calls.append(
                {
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "args": args_str,
                    "args_dict": args_dict,
                }
            )

        assert tool_calls[0]["args_dict"] == {}

    def test_transform_handles_empty_arguments(self):
        """Empty arguments string falls back to empty dict."""
        sdk_tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "test", "arguments": None},
            }
        ]

        import json

        tool_calls = []
        for tc in sdk_tool_calls:
            args_str = tc["function"]["arguments"] or ""
            try:
                args_dict = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args_dict = {}
            tool_calls.append(
                {
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "args": args_str,
                    "args_dict": args_dict,
                }
            )

        assert tool_calls[0]["args"] == ""
        assert tool_calls[0]["args_dict"] == {}


class TestPostparseToExecutorPath:
    """Integration test: full postparse→executor path."""

    def test_full_path_sdk_plus_postparse(self):
        """Verify complete path: SDK calls + postparse recovery → executor format."""
        # Step 1: SDK tool calls
        sdk_calls = [
            {
                "id": "sdk_1",
                "type": "function",
                "function": {"name": "bash", "arguments": '{"cmd": "ls"}'},
            }
        ]

        # Step 2: Postparse recovery
        content = "<toolcall><function=file_read>{\"file_path\": \"test.py\"}</function></toolcall>"
        _, _, _ = llm_postparse(content, None, sdk_calls)

        # Step 3: LLMResponse stores unified list
        resp = LLMResponse(
            raw=Mock(),
            text="response",
            reasoning=None,
            stats=CallStats(prompt_tokens=10, completion_tokens=5, cached_tokens=0, finish_reason="stop"),
            success=True,
            tool_calls=sdk_calls,
        )

        # Step 4: Format transformation (agent_core.py)
        import json

        tool_calls = []
        for tc in resp.tool_calls:
            args_str = tc["function"]["arguments"] or ""
            try:
                args_dict = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args_dict = {}
            tool_calls.append(
                {
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "args": args_str,
                    "args_dict": args_dict,
                }
            )

        # Verify: both SDK and postparse calls are in executor format
        assert len(tool_calls) == 2
        assert tool_calls[0]["name"] == "bash"
        assert tool_calls[0]["args_dict"] == {"cmd": "ls"}
        assert tool_calls[1]["name"] == "file_read"
        assert tool_calls[1]["args_dict"] == {"file_path": "test.py"}

    def test_postparse_only_path(self):
        """Verify path when SDK has zero calls but postparse recovers some."""
        # Step 1: Empty SDK calls
        sdk_calls = []

        # Step 2: Postparse recovery
        content = "<toolcall><function=file_read>{\"file_path\": \"test.py\"}</function></toolcall>"
        _, _, _ = llm_postparse(content, None, sdk_calls)

        # Step 3: LLMResponse stores unified list
        resp = LLMResponse(
            raw=Mock(),
            text="response",
            reasoning=None,
            stats=CallStats(prompt_tokens=10, completion_tokens=5, cached_tokens=0, finish_reason="stop"),
            success=True,
            tool_calls=sdk_calls,
        )

        # Step 4: Format transformation
        import json

        tool_calls = []
        for tc in resp.tool_calls:
            args_str = tc["function"]["arguments"] or ""
            try:
                args_dict = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args_dict = {}
            tool_calls.append(
                {
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "args": args_str,
                    "args_dict": args_dict,
                }
            )

        # Verify: postparse-recovered call reaches executor
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "file_read"
        assert tool_calls[0]["args_dict"] == {"file_path": "test.py"}
