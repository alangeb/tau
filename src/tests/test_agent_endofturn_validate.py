"""Tests for end-of-turn validation (detection-only)."""

from agent_endofturn_validate import ValidationError, ValidationErrorType, is_valid_end_of_turn


def test_valid_response_returns_none():
    result = is_valid_end_of_turn(
        response_text="This is a valid response.",
        finish_reason="stop",
        reasoning_content=None,
    )
    assert result is None


def test_empty_response_returns_validation_error():
    result = is_valid_end_of_turn(
        response_text="",
        finish_reason="stop",
        reasoning_content=None,
    )
    assert result is not None
    assert result.error_type == ValidationErrorType.EMPTY


def test_whitespace_only_response_returns_validation_error():
    result = is_valid_end_of_turn(
        response_text="   \n  \t  ",
        finish_reason="stop",
        reasoning_content=None,
    )
    assert result is not None
    assert result.error_type == ValidationErrorType.EMPTY


def test_truncated_response_returns_validation_error():
    result = is_valid_end_of_turn(
        response_text="This is a partial response that was cut off",
        finish_reason="length",
        reasoning_content=None,
    )
    assert result is not None
    assert result.error_type == ValidationErrorType.TRUNCATED


def test_unclosed_thinking_in_reasoning_returns_validation_error():
    result = is_valid_end_of_turn(
        response_text="Normal response text",
        finish_reason="stop",
        reasoning_content="<|begin_of_thought|>unclosed thought",
    )
    assert result is not None
    assert result.error_type == ValidationErrorType.UNCLOSED_THINKING_REASONING


def test_unclosed_thinking_in_response_returns_validation_error():
    result = is_valid_end_of_turn(
        response_text="<|begin_of_thought|>partial thought",
        finish_reason="stop",
        reasoning_content=None,
    )
    assert result is not None
    assert result.error_type == ValidationErrorType.UNCLOSED_THINKING_RESPONSE


def test_malformed_tool_call_syntax_returns_validation_error():
    # Build malformed tool-call string at runtime to avoid XML parsing issues
    close_slash = chr(60) + chr(47)  # "</"
    close_func = close_slash + "function>"
    close_param = close_slash + "parameter>"
    end_tok = chr(95)  # "_"
    malformed = "Done.\n" + close_param + "\n" + close_func + "\n" + end_tok
    result = is_valid_end_of_turn(
        response_text=malformed,
        finish_reason="stop",
        reasoning_content=None,
    )
    assert result is not None
    assert result.error_type == ValidationErrorType.MALFORMED_TOOL_CALL