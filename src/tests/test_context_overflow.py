"""Tests for context overflow detection and recovery.

Covers both the legacy error format and the newer vLLM/OpenAI-compatible
error format (context_length_exceeded / configured context size).
"""

import pytest

from agent_llm_invoke import _extract_token_count_from_error, _is_context_overflow
from agent_llm_models import CONTEXT_OVERFLOW_INDICATORS


class TestContextOverflowDetection:
    """Test _is_context_overflow detection for all error formats."""

    def test_legacy_openai_format(self):
        """Detect legacy OpenAI 'maximum context length' format."""
        err = ('{"error":{"message":"This model maximum context length is '
                '200000 tokens. However, you have 214856 tokens"}}')
        assert _is_context_overflow(err) is True

    def test_legacy_llamacpp_format(self):
        """Detect 'context size has been exceeded' format."""
        err = 'error: context size has been exceeded'
        assert _is_context_overflow(err) is True

    def test_vllm_context_length_exceeded(self):
        """Detect vLLM 'context_length_exceeded' error code."""
        err = ('{"error":{"code":"context_length_exceeded","message":"Prompt '
                'has 214856 tokens, but the configured context size is 200000"}}')
        assert _is_context_overflow(err) is True

    def test_configured_context_size(self):
        """Detect 'configured context size is' message format."""
        err = ('BadRequestError: {"error":{"message":"Prompt has 214856 tokens, '
                'but the configured context size is 200000 tokens"}}')
        assert _is_context_overflow(err) is True

    def test_combined_format(self):
        """Detect error with both context_length_exceeded and configured context size."""
        err = ('BadRequestError: {"error":{"message":"Prompt has 214856 tokens, '
                'but the configured context size is 200000 tokens","type":'
                '"invalid_request_error","code":"context_length_exceeded",'
                '"n_prompt_tokens":214856,"n_ctx":200000}}')
        assert _is_context_overflow(err) is True

    def test_bad_request_not_overflow(self):
        """Generic bad request should NOT match."""
        err = '{"error":{"message":"invalid parameter: temperature"}}'
        assert _is_context_overflow(err) is False

    def test_invalid_request_error_not_overflow(self):
        """invalid_request_error alone should NOT match (too broad)."""
        err = '{"error":{"type":"invalid_request_error","message":"bad tool args"}}'
        assert _is_context_overflow(err) is False

    def test_unknown_tool_not_overflow(self):
        """Unknown tool error should NOT match."""
        err = 'Error: unknown tool: nonexistent_tool'
        assert _is_context_overflow(err) is False

    def test_empty_string(self):
        assert _is_context_overflow("") is False

    def test_all_indicators_present(self):
        """Verify all expected indicators are in CONTEXT_OVERFLOW_INDICATORS."""
        expected = [
            "context_length_exceeded",
            "configured context size is",
            "maximum context length",
            "context size has been exceeded",
        ]
        for indicator in expected:
            assert indicator in CONTEXT_OVERFLOW_INDICATORS, (
                f"Missing indicator: {indicator}"
            )


class TestExtractTokenCountFromError:
    """Test _extract_token_count_from_error for all formats."""

    def test_legacy_format_at_least_tokens(self):
        """Extract from 'at least NNNNNN input tokens' format."""
        assert (
            _extract_token_count_from_error(
                "your prompt contains at least 188001 input tokens"
            )
            == 188001
        )

    def test_vllm_has_tokens_format(self):
        """Extract from 'has NNNNNN tokens' format (vLLM)."""
        assert (
            _extract_token_count_from_error(
                "Prompt has 214856 tokens, but the configured context size is 200000"
            )
            == 214856
        )

    def test_n_prompt_tokens_in_full_error(self):
        """Extract from full error containing n_prompt_tokens field."""
        err = ('{"n_prompt_tokens":214856,"n_ctx":200000,"message":'
                '"Prompt has 214856 tokens"}')
        assert _extract_token_count_from_error(err) == 214856

    def test_full_vllm_error(self):
        """Extract from full vLLM error message."""
        err = ('BadRequestError: {"error":{"message":"Prompt has 214856 tokens, '
                'but the configured context size is 200000 tokens","type":'
                '"invalid_request_error","code":"context_length_exceeded",'
                '"n_prompt_tokens":214856,"n_ctx":200000}}')
        assert _extract_token_count_from_error(err) == 214856

    def test_no_tokens_returns_none(self):
        """Non-overflow errors return None."""
        assert _extract_token_count_from_error("some other error") is None

    def test_empty_string_returns_none(self):
        assert _extract_token_count_from_error("") is None
