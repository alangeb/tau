"""Token tracking for agent sessions.

Base class for ``AgentSessionManager``. Provides token accounting logic
(session totals, per-turn snapshots, and cache tracking) as a reusable
single-responsibility class. ``AgentSessionManager`` inherits from this
to avoid composition boilerplate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_llm_models import CallStats, CacheTracker


@dataclass
class TokenTracker:
    """Track token usage for an agent session.

    Maintains session-wide totals (input, output, cached), per-turn
    snapshots, and its own CacheTracker for per-agent cache statistics.

    Uses actual API values when available; falls back to estimates
    when the API does not return exact counts.
    """

    # Session totals
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0

    # Session byte estimates (roughly 4 bytes/token for UTF-8)
    input_bytes: int = 0
    output_bytes: int = 0
    cached_bytes: int = 0

    # Last-turn counters
    last_turn_input_tokens: int = 0
    last_turn_output_tokens: int = 0
    last_turn_cached_tokens: int = 0

    # Exact context tokens from API (None = estimated)
    last_exact_context_tokens: int | None = None

    # Per-agent cache tracker — isolated from other agents/forks
    _cache_tracker: CacheTracker = field(default_factory=CacheTracker, repr=False)

    @property
    def cache_tracker(self) -> CacheTracker:
        """Per-agent cache tracker."""
        return self._cache_tracker

    def record_call_stats(self, stats: CallStats) -> None:
        """Record token usage from a single LLM call and update counters.

        Mirrors the inline token-recording logic in invoke_with_tools_loop().
        """
        pt = stats.prompt_tokens or 0
        ct = stats.completion_tokens or 0
        cached = stats.cached_tokens or 0

        self.last_turn_input_tokens = pt
        self.last_turn_output_tokens = ct
        self.last_turn_cached_tokens = cached

        self.input_tokens += pt
        self.output_tokens += ct
        self.cached_tokens += cached

        # Estimate bytes (roughly 4 bytes/token for UTF-8)
        self.input_bytes += pt * 4
        self.output_bytes += ct * 4
        self.cached_bytes += cached * 4

        self.cache_tracker.record(stats)

        # Track exact context tokens from the API when available.
        if stats.prompt_tokens is not None and stats.prompt_tokens > 0:
            self.last_exact_context_tokens = stats.prompt_tokens
        else:
            self.last_exact_context_tokens = None

    def clear_tokens(self) -> None:
        """Reset all token counters and the per-agent cache tracker."""
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_tokens = 0
        self.input_bytes = 0
        self.output_bytes = 0
        self.cached_bytes = 0
        self.last_turn_input_tokens = 0
        self.last_turn_output_tokens = 0
        self.last_turn_cached_tokens = 0
        self.last_exact_context_tokens = None
        self._cache_tracker.clear()

    def reset_last_turn(self) -> None:
        """Reset only last-turn counters (preserves session totals)."""
        self.last_turn_input_tokens = 0
        self.last_turn_output_tokens = 0
        self.last_turn_cached_tokens = 0
        self.last_exact_context_tokens = None