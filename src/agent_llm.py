"""LLM module facade for TauErgon.

Re-exports everything from the focused sub-modules:
  - agent_llm_models.py      (data models, error classes, config, constants)
  - agent_llm_cache.py       (PrefixCacheTracker)
  - agent_llm_validation.py  (InvalidReplyError, llm_validate)
  - agent_llm_client.py      (SimpleOpenAIClient, RetryBackoff)
  - agent_llm_invoke.py      (_invoke_llm_with_retry, helpers)
  - agent_llm_tool_parse.py  (tool-call parsing constants and llm_postparse)

CRITICAL: Keep token delimiters obfuscated via constants.
Do not inline raw tag literals or "simplify" this during refactors.
Some model/runtime pathways are sensitive to direct tag tokens in source.
"""

from __future__ import annotations

# Re-export tool-call parsing constants and functions.
from agent_llm_tool_parse import (
    ANTHROPIC_MAX_BODY_LEN,
    ARGUMENTS,
    BEGIN_OF_THOUGHT,
    END_OF_THOUGHT,
    FUNCTION,
    GT,
    INCOMPLETE_TOOL_CALL_PATTERNS,
    LT,
    LT_PIPE,
    LT_SLASH,
    PARAMETER_ALT,
    PIPE_GT,
    REASON,
    REASONING,
    THINK,
    THINKING,
    THINKING_TAG_PAIRS,
    TOOL,
    TOOLCALL,
    TOOL_CALL_ALT,
    TOOL_CALL_PATTERNS,
    TOOL_USE,
    TOOL_USE_CLOSE,
    TOOL_USE_OPEN,
    llm_postparse,
)

# Data models, error classes, config, constants
from agent_llm_models import (
    _ALLOWED_TOOL_CALL_FIELDS,
    _ToolCall,
    _ToolCallFunction,
    ALLOWED_MESSAGE_FIELDS,
    APIConnectionError,
    APIError,
    APITimeoutError,
    BadRequestError,
    CallStats,
    CacheTracker,
    Choice,
    COMPRESSION_TARGET_RATIO,
    CONTEXT_OVERFLOW_INDICATORS,
    DEFAULT_MAX_CONTEXT_TOKENS,
    DEFAULT_MAX_OUTPUT_TOKENS,
    EmptyModelResponse,
    Function,
    LLMCallConfig,
    LLMResponse,
    Message,
    OPENAI_BODY_PARAMS,
    OVERSIZED_THRESHOLD,
    RateLimitError,
    Response,
    ToolCall,
    UnauthorizedError,
    Usage,
)

# Cache tracking
from agent_llm_cache import PrefixCacheTracker

# Validation
from agent_llm_validation import (
    _VALIDATORS,
    _strip_phantoms,
    InvalidReplyError,
    llm_validate,
)

# HTTP client
from agent_llm_client import (
    _HTTP_ERROR_MAP,
    _is_context_overflow,
    RetryBackoff,
    SimpleChatCompletion,
    SimpleOpenAIClient,
)

# Invocation
from agent_llm_invoke import (
    _build_call_kwargs,
    _build_llm_response,
    _extract_call_stats,
    _extract_token_usage,
    _handle_context_overflow,
    _invoke_llm_with_retry,
    _prepare_messages,
    _try_context_compress,
    _try_oversized_redaction,
)


# ── Auto-derived __all__ ─────────────────────────────────────────────────────
# Every name imported above is an intentional re-export.
# Build __all__ programmatically so it can NEVER drift from the imports.
# Adding/removing an import is the ONLY change needed — no __all__ edits.

def _build_all() -> list[str]:
    return sorted(
        name for name in globals()
        # Exclude dunders (__name__, __file__, ...), this function, and __future__ artifact
        if not name.startswith("__") and name not in ("_build_all", "annotations")
    )


__all__ = _build_all()
