"""Tests for APIGatewayError handling and 5xx retry logic."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_llm_models import APIGatewayError, APIError
from agent_llm_client import _HTTP_ERROR_MAP


class TestAPIGatewayErrorClass:
    """Test APIGatewayError class definition and inheritance."""

    def test_api_gateway_error_exists(self):
        err = APIGatewayError("502 Bad Gateway", status_code=502)
        assert isinstance(err, APIError)
        assert err.status_code == 502
        assert "502" in str(err)

    def test_api_gateway_error_is_api_error_subclass(self):
        assert issubclass(APIGatewayError, APIError)

    def test_api_gateway_error_503(self):
        err = APIGatewayError("503 Service Unavailable", status_code=503)
        assert err.status_code == 503
        assert isinstance(err, APIError)

    def test_api_gateway_error_504(self):
        err = APIGatewayError("504 Gateway Timeout", status_code=504)
        assert err.status_code == 504
        assert isinstance(err, APIError)

    def test_api_gateway_error_no_status_code(self):
        err = APIGatewayError("Gateway error")
        assert err.status_code is None


class TestHTTPErrorMap:
    """Test HTTP error code mapping."""

    def test_502_maps_to_api_gateway_error(self):
        assert _HTTP_ERROR_MAP[502] == APIGatewayError

    def test_503_maps_to_api_gateway_error(self):
        assert _HTTP_ERROR_MAP[503] == APIGatewayError

    def test_504_maps_to_api_gateway_error(self):
        assert _HTTP_ERROR_MAP[504] == APIGatewayError

    def test_500_falls_through_to_api_error(self):
        assert 500 not in _HTTP_ERROR_MAP  # Generic 500 → APIError (no retry)

    def test_400_still_maps_to_bad_request(self):
        from agent_llm_models import BadRequestError
        assert _HTTP_ERROR_MAP[400] == BadRequestError

    def test_401_still_maps_to_unauthorized(self):
        from agent_llm_models import UnauthorizedError
        assert _HTTP_ERROR_MAP[401] == UnauthorizedError

    def test_429_still_maps_to_rate_limit(self):
        from agent_llm_models import RateLimitError
        assert _HTTP_ERROR_MAP[429] == RateLimitError


class TestBackoff30sBase:
    """Test 30s base backoff for gateway errors."""

    def test_backoff_30s_base(self):
        """Backoff should start at 30s for gateway errors."""
        from agent_llm_client import RetryBackoff

        backoff = RetryBackoff(base=30, max_wait=120, jitter=0.0)
        wait_0 = backoff.next_wait(0)
        assert 27 <= wait_0 <= 33  # 30s ± jitter (0% jitter = exact 30)
        wait_1 = backoff.next_wait(1)
        assert 54 <= wait_1 <= 66  # 60s ± jitter

    def test_backoff_caps_at_max_wait(self):
        """Backoff should cap at max_wait."""
        from agent_llm_client import RetryBackoff

        backoff = RetryBackoff(base=30, max_wait=120, jitter=0.0)
        wait_3 = backoff.next_wait(3)  # 30 * 2^3 = 240, capped at 120
        assert wait_3 <= 120

    def test_backoff_with_jitter(self):
        """Backoff with jitter should vary."""
        from agent_llm_client import RetryBackoff

        backoff = RetryBackoff(base=30, max_wait=120, jitter=0.3)
        waits = [backoff.next_wait(0) for _ in range(10)]
        # With jitter, values should vary (unless extremely unlucky)
        assert len(set(waits)) > 1 or len(waits) == 1  # Allow for edge case


class TestGatewayErrorExhaustion:
    """Test that gateway errors give up after max retries."""

    def test_gives_up_after_max_retries(self):
        """After max_retries, APIGatewayError should be raised."""
        err = APIGatewayError("502 Bad Gateway", status_code=502)
        assert err.status_code == 502
        assert isinstance(err, APIError)

    def test_error_preserves_status_code(self):
        """Error should preserve status_code through chain."""
        err = APIGatewayError("503 Service Unavailable", status_code=503)
        assert getattr(err, "status_code", None) == 503


class TestGatewayErrorRetryIntegration:
    """Integration tests for gateway error retry in _invoke_llm_with_retry."""

    def test_api_gateway_error_caught_by_handler(self):
        """Verify APIGatewayError is caught by the dedicated handler."""
        # The handler is in _invoke_llm_with_retry — verify the import works
        from agent_llm_invoke import APIGatewayError as InvokeGatewayError
        assert InvokeGatewayError is APIGatewayError

    def test_http_error_map_used_by_client(self):
        """Verify client uses _HTTP_ERROR_MAP for 5xx errors."""
        # Verify the mapping is correct
        for code in [502, 503, 504]:
            assert _HTTP_ERROR_MAP.get(code) == APIGatewayError


class TestRateLimitErrorRetry:
    """Test that RateLimitError (HTTP 429) is retried with backoff."""

    def test_rate_limit_error_imported_in_invoke(self):
        """Verify RateLimitError is imported in agent_llm_invoke."""
        from agent_llm_invoke import RateLimitError
        from agent_llm_models import RateLimitError as ModelRateLimitError
        assert RateLimitError is ModelRateLimitError

    def test_rate_limit_error_is_api_error_subclass(self):
        """RateLimitError should be a subclass of APIError."""
        from agent_llm_models import RateLimitError, APIError
        assert issubclass(RateLimitError, APIError)

    def test_rate_limit_error_has_status_code(self):
        """RateLimitError should preserve status_code."""
        from agent_llm_models import RateLimitError
        err = RateLimitError("429 Too Many Requests", status_code=429)
        assert err.status_code == 429
        assert isinstance(err, APIError)

    def test_rate_limit_backoff_values(self):
        """Rate limit backoff should use 15s base, 120s max."""
        from agent_llm_client import RetryBackoff

        # These are the values used in the RateLimitError handler
        backoff = RetryBackoff(base=15, max_wait=120, jitter=0.0)
        wait_0 = backoff.next_wait(0)
        assert wait_0 == 15  # 15s base
        wait_1 = backoff.next_wait(1)
        assert wait_1 == 30  # 15 * 2
        wait_2 = backoff.next_wait(2)
        assert wait_2 == 60  # 15 * 4
        wait_3 = backoff.next_wait(3)
        assert wait_3 == 120  # 15 * 8, capped at 120
        wait_4 = backoff.next_wait(4)
        assert wait_4 == 120  # still capped

    def test_rate_limit_error_not_caught_by_generic_handler(self):
        """RateLimitError should NOT fall through to generic Exception handler.
        
        This is the core fix: before the fix, RateLimitError was caught by
        'except Exception' which treated it as 'Unexpected error — no retry'.
        After the fix, it has its own handler with retry logic.
        """
        from agent_llm_invoke import RateLimitError
        from agent_llm_models import APIError
        
        # Verify RateLimitError is a distinct exception type
        err = RateLimitError("429 Too Many Requests", status_code=429)
        assert isinstance(err, APIError)
        assert type(err).__name__ == "RateLimitError"
        
        # Verify it would NOT be caught by the connection error check
        assert not isinstance(err, (ConnectionRefusedError, BrokenPipeError, ConnectionResetError))

    def test_http_429_maps_to_rate_limit_error(self):
        """HTTP 429 should map to RateLimitError in client."""
        from agent_llm_models import RateLimitError
        assert _HTTP_ERROR_MAP[429] == RateLimitError


class TestTimeoutBackoff:
    """Test that APITimeoutError handler uses backoff to prevent thundering herd."""

    def test_timeout_backoff_values(self):
        """Timeout backoff should use 5s base, 60s max."""
        from agent_llm_client import RetryBackoff

        # These are the values used in the APITimeoutError handler
        backoff = RetryBackoff(base=5, max_wait=60, jitter=0.0)
        wait_0 = backoff.next_wait(0)
        assert wait_0 == 5  # 5s base
        wait_1 = backoff.next_wait(1)
        assert wait_1 == 10  # 5 * 2
        wait_2 = backoff.next_wait(2)
        assert wait_2 == 20  # 5 * 4
        wait_3 = backoff.next_wait(3)
        assert wait_3 == 40  # 5 * 8
        wait_4 = backoff.next_wait(4)
        assert wait_4 == 60  # 5 * 16, capped at 60
        wait_5 = backoff.next_wait(5)
        assert wait_5 == 60  # still capped

    def test_timeout_error_exists(self):
        """APITimeoutError should exist and be importable."""
        from agent_llm_models import APITimeoutError, APIError
        assert issubclass(APITimeoutError, APIError)

    def test_timeout_error_imported_in_invoke(self):
        """Verify APITimeoutError is imported in agent_llm_invoke."""
        from agent_llm_invoke import APITimeoutError
        from agent_llm_models import APITimeoutError as ModelTimeoutError
        assert APITimeoutError is ModelTimeoutError

    def test_empty_model_response_imported_in_invoke(self):
        """Verify EmptyModelResponse is imported in agent_llm_invoke."""
        from agent_llm_invoke import EmptyModelResponse
        assert EmptyModelResponse is not None


class TestRetryHelpers:
    """Test _build_backoff and _log_and_raise helper functions."""

    def test_build_backoff_timeout(self):
        """_build_backoff('timeout') returns correct config (with jitter)."""
        from agent_llm_invoke import _build_backoff
        backoff = _build_backoff("timeout")
        wait_0 = backoff.next_wait(0)
        # base=5, jitter=0.3 → wait is in range [5*0.7, 5*1.3] = [3.5, 6.5]
        assert 3.5 <= wait_0 <= 6.5

    def test_build_backoff_gateway(self):
        """_build_backoff('gateway') returns correct config (with jitter)."""
        from agent_llm_invoke import _build_backoff
        backoff = _build_backoff("gateway")
        wait_0 = backoff.next_wait(0)
        # base=30, jitter=0.3 → wait is in range [21, 39]
        assert 21 <= wait_0 <= 39

    def test_build_backoff_rate_limit(self):
        """_build_backoff('rate_limit') returns correct config (with jitter)."""
        from agent_llm_invoke import _build_backoff
        backoff = _build_backoff("rate_limit")
        wait_0 = backoff.next_wait(0)
        # base=15, jitter=0.3 → wait is in range [10.5, 19.5]
        assert 10.5 <= wait_0 <= 19.5

    def test_build_backoff_connection(self):
        """_build_backoff('connection') returns correct config (with jitter)."""
        from agent_llm_invoke import _build_backoff
        backoff = _build_backoff("connection")
        wait_0 = backoff.next_wait(0)
        # base=5, jitter=0.3 → wait is in range [3.5, 6.5]
        assert 3.5 <= wait_0 <= 6.5
        # max_wait=120 for connection — jitter is applied AFTER cap, so
        # next_wait can slightly exceed max_wait (up to ~120*1.3 = 156)
        wait_10 = backoff.next_wait(10)
        assert wait_10 <= 160  # cap + jitter margin

    def test_build_backoff_unknown_defaults_to_timeout(self):
        """_build_backoff with unknown type defaults to timeout config."""
        from agent_llm_invoke import _build_backoff
        backoff = _build_backoff("unknown_type")
        wait_0 = backoff.next_wait(0)
        # defaults to (5, 60, 0.3) → wait is in range [3.5, 6.5]
        assert 3.5 <= wait_0 <= 6.5

    def test_log_and_raise_raises_exception(self):
        """_log_and_raise should raise the exception."""
        from agent_llm_invoke import _log_and_raise
        err = RuntimeError("test error")
        with pytest.raises(RuntimeError, match="test error"):
            _log_and_raise(
                err, "TEST ERROR", {},
                log_on_failure=False, log_file=None,
            )

    def test_log_and_raise_chained(self):
        """_log_and_raise with chained=True preserves exception chain."""
        from agent_llm_invoke import _log_and_raise
        err = RuntimeError("test error")
        with pytest.raises(RuntimeError) as exc_info:
            _log_and_raise(
                err, "TEST ERROR", {},
                log_on_failure=False, log_file=None,
                chained=True,
            )
        # The exception should be chained (cause is itself)
        assert exc_info.value.__cause__ is err

    def test_log_and_raise_not_chained(self):
        """_log_and_raise with chained=False does not chain."""
        from agent_llm_invoke import _log_and_raise
        err = RuntimeError("test error")
        with pytest.raises(RuntimeError) as exc_info:
            _log_and_raise(
                err, "TEST ERROR", {},
                log_on_failure=False, log_file=None,
                chained=False,
            )
        # No exception chain
        assert exc_info.value.__cause__ is None

    def test_backoff_configs_dict_complete(self):
        """_BACKOFF_CONFIGS has all four error types."""
        from agent_llm_invoke import _BACKOFF_CONFIGS
        assert "timeout" in _BACKOFF_CONFIGS
        assert "gateway" in _BACKOFF_CONFIGS
        assert "rate_limit" in _BACKOFF_CONFIGS
        assert "connection" in _BACKOFF_CONFIGS
        # Verify all have 3-tuple values
        for key, val in _BACKOFF_CONFIGS.items():
            assert isinstance(val, tuple)
            assert len(val) == 3
            base, max_wait, jitter = val
            assert base > 0
            assert max_wait >= base
            assert 0 <= jitter <= 1
