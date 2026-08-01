"""Loop detection for TauErgon tool call sequences.

Detects repetitive and cyclical tool-call patterns indicating potential infinite loops:
1. Consecutive repeat detection: warns after repeat_threshold identical calls (default: 3)
2. Shannon entropy analysis: warns when entropy drops below 1.5 over rolling window (default: 30)

Key class:
- LoopDetector: Main detection class with configurable window_size and repeat_threshold

Escalation levels (warnings accumulate monotonically, no reset):
- Level 0: No escalation (normal operation, <3 warnings)
- Level 1: Alert warnings prepended to tool output (warnings 3-5)
- Level 2: Simulated self-reflection via synthetic think calls (warnings 6-8)
- Level 3: Guided introspection with structured user questions (warnings 9-11)
- Level 4: Forced analysis with deep introspection (warnings 12-14)
- Level 5: Termination — force_end_turn (warnings 15+)

System-initiated tool calls (e.g., synthetic think/end_turn) are excluded from
detection via the system_call flag to avoid polluting loop patterns.
"""

from __future__ import annotations

import json
import math
from collections import Counter, deque

# Escalating warning message templates
WARNING_LEVEL_1 = (
    "⚠️ LOOP WARNING #{warning_count}: Tool '{tool_name}' called {consecutive} times consecutively. "
    "This is warning #{warning_count} this turn. Consider changing your approach."
)

WARNING_LEVEL_2 = (
    "🔴 LOOP WARNING #{warning_count}: Tool '{tool_name}' called {consecutive} times consecutively. "
    "This is warning #{warning_count} this turn. You appear stuck in a loop. "
    "Use the 'think' tool to re-analyze the situation before continuing."
)

WARNING_LEVEL_3 = (
    "🚨 CRITICAL LOOP #{warning_count}: Tool '{tool_name}' repeated {consecutive} times. "
    "Warning #{warning_count} this turn. You MUST use the 'think' tool now. "
    "Do not call any other tools until you have analyzed and planned."
)

# Entropy warning templates (parallel to WARNING_LEVEL_*)
ENTROPY_WARNING_LEVEL_1 = (
    "⚠️ LOW ENTROPY #{warning_count}: Tool '{tool_name}' pattern "
    "highly predictable (entropy: {entropy:.2f}). "
    "Consider using 'think' to re-analyze."
)

ENTROPY_WARNING_LEVEL_2 = (
    "🔴 ENTROPY WARNING #{warning_count}: Tool '{tool_name}' pattern "
    "highly predictable (entropy: {entropy:.2f}). "
    "Use the 'think' tool to re-analyze the situation."
)

ENTROPY_WARNING_LEVEL_3 = (
    "🚨 CRITICAL ENTROPY #{warning_count}: Tool '{tool_name}' pattern "
    "highly predictable (entropy: {entropy:.2f}). "
    "You MUST use the 'think' tool now."
)

# Grouped templates: index = escalation_level-1 (clamped to 0..2)
_WARNING_TEMPLATES = [WARNING_LEVEL_1, WARNING_LEVEL_2, WARNING_LEVEL_3]
_ENTROPY_TEMPLATES = [ENTROPY_WARNING_LEVEL_1, ENTROPY_WARNING_LEVEL_2, ENTROPY_WARNING_LEVEL_3]
# Sustained entropy warning templates (for cycles above 1.5 threshold)
SUSTAINED_ENTROPY_WARNING_LEVEL_1 = (
    "⚠️ SUSTAINED LOW ENTROPY #{warning_count}: Tool pattern has been highly predictable "
    "for {sustained_window} consecutive windows (entropy: {entropy:.2f}). "
    "This indicates a likely infinite loop. Use 'think' to re-analyze immediately."
)

SUSTAINED_ENTROPY_WARNING_LEVEL_2 = (
    "🔴 SUSTAINED ENTROPY WARNING #{warning_count}: Tool pattern has been highly predictable "
    "for {sustained_window} consecutive windows (entropy: {entropy:.2f}). "
    "You appear stuck in a loop. Use the 'think' tool to re-analyze."
)

SUSTAINED_ENTROPY_WARNING_LEVEL_3 = (
    "🚨 CRITICAL SUSTAINED ENTROPY #{warning_count}: Tool pattern has been highly predictable "
    "for {sustained_window} consecutive windows (entropy: {entropy:.2f}). "
    "You MUST use the 'think' tool now. Do not call any other tools until you have analyzed."
)

_SUSTAINED_ENTROPY_TEMPLATES = [SUSTAINED_ENTROPY_WARNING_LEVEL_1, SUSTAINED_ENTROPY_WARNING_LEVEL_2, SUSTAINED_ENTROPY_WARNING_LEVEL_3]


__all__ = ["LoopDetector"]


class LoopDetector:
    """Detect repetitive or cyclical tool-call patterns.

    1. **Repeat**: Warns after *repeat_threshold* identical consecutive calls.
    2. **Entropy**: Warns when Shannon entropy over the last *window_size* calls
       drops below 1.5 (highly predictable pattern).
    3. **Escalation**: Tracks cumulative warnings and escalates intervention level.
    4. **Unknown tool tracking**: Tracks tool names that failed because they
       don't exist. When *replace_unknown_tools* >= 2, replaces repeated
       unknown tool calls with a `think` call for self-correction.
    """

    def __init__(
        self,
        window_size: int = 30,
        repeat_threshold: int = 3,
        # replace_unknown_tools: N means "after N repeated calls to a non-existent tool,
        # replace with think() for self-correction. Default 0 (disabled) here, but
        # tau.json overrides this to 2 at runtime. Changing this default won't affect
        # production unless tau.json is also updated.
        replace_unknown_tools: int = 0,
        warn_threshold: int = 3,
        inject_threshold: int = 7,
        force_think_threshold: int = 11,
        end_turn_threshold: int = 15,
        # Sustained entropy tracking parameters
        sustained_window: int = 3,
        sustained_threshold: float = 2.5,
    ):
        self.window_size = window_size
        self.repeat_threshold = repeat_threshold
        self.replace_unknown_tools = replace_unknown_tools
        self.warn_threshold = warn_threshold
        self.inject_threshold = inject_threshold
        self.force_think_threshold = force_think_threshold
        self.end_turn_threshold = end_turn_threshold

        self.tool_call_history: deque[str] = deque(maxlen=window_size)
        self.consecutive_repeats = 0
        self.last_tool_call: str | None = None

        # Entropy warnings contribute only 0.5 toward escalation thresholds
        # (predictable pattern ≠ exact loop).
        self.total_warnings = 0
        self.entropy_warnings = 0
        self.tool_warnings: dict[str, int] = {}
        self.escalation_level = 0

        # Unknown tool tracking: tool_name -> call_count (per-turn, resets with reset())
        self.failed_tool_names: dict[str, int] = {}

        # Sustained entropy tracking (catches cycles above 1.5 threshold)
        self.sustained_window = sustained_window
        self.sustained_threshold = sustained_threshold
        self._entropy_history: deque[float] = deque(maxlen=sustained_window)

    def _tool_call_key(self, tool_name: str, args: dict) -> str:
        """Serialize tool name and arguments into a comparable string key."""
        try:
            args_json = json.dumps(args, sort_keys=True)
        except (TypeError, ValueError):
            args_json = json.dumps({k: str(v) for k, v in sorted(args.items())})
        return f"{tool_name}:{args_json}"

    @staticmethod
    def _select_template(level: int, templates: list[str]) -> str:
        """Select a template by escalation level, clamped to valid range."""
        idx = min(max(level - 1, 0), len(templates) - 1)
        return templates[idx]

    def _get_warning_message(self, tool_name: str) -> str:
        template = self._select_template(self.escalation_level, _WARNING_TEMPLATES)
        return template.format(
            warning_count=self.total_warnings,
            tool_name=tool_name,
            consecutive=self.consecutive_repeats,
        )

    def _get_entropy_warning(self, tool_name: str, entropy: float) -> str:
        template = self._select_template(self.escalation_level, _ENTROPY_TEMPLATES)
        return template.format(
            warning_count=self._display_warning_count(),
            tool_name=tool_name,
            entropy=entropy,
        )

    def _get_sustained_entropy_warning(self, entropy: float) -> str:
        """Build sustained entropy warning message.

        NOTE: `tool_name` parameter removed — templates don't use it.
        """
        template = self._select_template(self.escalation_level, _SUSTAINED_ENTROPY_TEMPLATES)
        return template.format(
            warning_count=self._display_warning_count(),
            entropy=entropy,
            sustained_window=self.sustained_window,
        )

    def _display_warning_count(self) -> int:
        """Total human-readable warning count (repeat + entropy)."""
        return self.total_warnings + self.entropy_warnings

    def _update_escalation_level(self) -> None:
        """Update escalation level based on total_warnings.

        New level structure (based on total_warnings, not effective_warnings):
        - Level 0: <3 warnings (no escalation)
        - Level 1: 3-5 warnings (alert)
        - Level 2: 6-8 warnings (simulated self-reflection)
        - Level 3: 9-11 warnings (guided introspection)
        - Level 4: 12-14 warnings (forced analysis)
        - Level 5: 15+ warnings (termination)
        """
        if self.total_warnings >= 15:
            self.escalation_level = 5
        elif self.total_warnings >= 12:
            self.escalation_level = 4
        elif self.total_warnings >= 9:
            self.escalation_level = 3
        elif self.total_warnings >= 6:
            self.escalation_level = 2
        elif self.total_warnings >= 3:
            self.escalation_level = 1
        else:
            self.escalation_level = 0

    def detect_tool_loop(self, tool_name: str, args: dict, system_call: bool = False) -> str | None:
        """Check if the current tool call indicates a loop.

        Args:
            tool_name: Name of the tool being called.
            args: Tool arguments.
            system_call: If True, skip tracking (system-initiated calls like
                synthetic think/end_turn should not pollute loop detection).

        Returns a warning message if a loop is detected, or None otherwise.
        """
        if system_call:
            return None
        key = self._tool_call_key(tool_name, args)
        self.tool_call_history.append(key)

        if key == self.last_tool_call:
            self.consecutive_repeats += 1
        else:
            self.consecutive_repeats = 1
            self.last_tool_call = key
            # Non-repeat call: reset repeat warnings (loop condition broken).
            # Also check entropy — if recovered, reset entropy warnings too.
            self.total_warnings = 0
            if len(self.tool_call_history) < 10:
                # Not enough history for entropy — reset everything.
                self.entropy_warnings = 0
                self._entropy_history.clear()
            else:
                entropy = self._calculate_entropy()
                if entropy >= self.sustained_threshold:
                    # Entropy recovered — reset entropy warnings.
                    self.entropy_warnings = 0
                    self._entropy_history.clear()
                # If entropy still low, keep entropy_warnings and history.
            # Recalculate escalation from remaining warnings (may be 0 now).
            self._update_escalation_level()

        if self.consecutive_repeats >= self.repeat_threshold:
            self.total_warnings += 1
            self.tool_warnings[tool_name] = self.tool_warnings.get(tool_name, 0) + 1
            self._update_escalation_level()
            return self._get_warning_message(tool_name)

        # Entropy-based detection (both instantaneous and sustained)
        if len(self.tool_call_history) >= 10:
            entropy = self._calculate_entropy()
            self._entropy_history.append(entropy)

            # Check for sustained low entropy (catches cycles above 1.5 threshold)
            if len(self._entropy_history) >= self.sustained_window:
                recent_entropies = list(self._entropy_history)[-self.sustained_window:]
                if all(e < self.sustained_threshold for e in recent_entropies):
                    self.entropy_warnings += 1
                    self.tool_warnings[tool_name] = self.tool_warnings.get(tool_name, 0) + 1
                    self._update_escalation_level()
                    return self._get_sustained_entropy_warning(entropy)

        return None

    def _calculate_entropy(self) -> float:
        """Calculate Shannon entropy of tool call patterns in the history."""
        if not self.tool_call_history:
            return 0.0
        counts = Counter(self.tool_call_history)
        total = len(self.tool_call_history)
        return -sum((c / total) * math.log2(c / total) for c in counts.values())

    def get_escalation_info(self) -> dict:
        """Return current escalation state and derived flags."""
        return {
            "total_warnings": self.total_warnings,
            "entropy_warnings": self.entropy_warnings,
            "escalation_level": self.escalation_level,
            "tool_warnings": dict(self.tool_warnings),
            "needs_injection": self.escalation_level >= 2,
            "needs_force_think": self.escalation_level >= 3,
        }

    def reset(self) -> None:
        """Clear all detection state and reset counters.

        NOTE: Only called at turn start (agent_core.py). No longer called
        during escalation — warnings now accumulate monotonically.
        """
        self.tool_call_history.clear()
        self.consecutive_repeats = 0
        self.last_tool_call = None
        self.total_warnings = 0
        self.entropy_warnings = 0
        self.tool_warnings = {}
        self.escalation_level = 0
        self.failed_tool_names.clear()
        # Reset sustained entropy tracking
        self._entropy_history.clear()

    def record_unknown_tool(self, tool_name: str) -> int:
        """Record an unknown tool call. Returns the cumulative count for this name.

        Tracks tool names that failed because they don't exist in TOOLS.
        Used to decide whether to replace repeated unknown tool calls with think.
        """
        count = self.failed_tool_names.get(tool_name, 0) + 1
        self.failed_tool_names[tool_name] = count
        return count

    def should_replace_unknown(self, tool_name: str) -> bool:
        """Check if an unknown tool call should be replaced with think.

        Returns True when the tool has been called enough times to warrant
        replacement. Threshold is self.replace_unknown_tools (0 = off).
        """
        if self.replace_unknown_tools <= 0:
            return False
        return self.failed_tool_names.get(tool_name, 0) >= self.replace_unknown_tools

    def get_stats(self) -> dict:
        """Return current detection statistics."""
        return {
            "history_size": len(self.tool_call_history),
            "consecutive_repeats": self.consecutive_repeats,
            "entropy": self._calculate_entropy() if self.tool_call_history else 0.0,
        }
