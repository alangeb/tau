"""Loop escalation management for TauErgon.

Handles loop detection escalation, reflection injection, and recovery from
invalid end-of-turn states. Extracted from the TauErgon god class to provide
a focused, single-responsibility module for loop-related concerns.

Key class:
- LoopEscalationManager: Orchestrates loop escalation, recovery, and reflection

Escalation ladder (warnings accumulate monotonically, no reset):
- Level 1 (warnings 3-5): Alert warnings prepended to tool output
- Level 2 (warnings 6-8): Simulated self-reflection via synthetic think calls
- Level 3 (warnings 9-11): Guided introspection with structured user questions
- Level 4 (warnings 12-14): Forced analysis with deep introspection
- Level 5 (warnings 15+): Termination — force_end_turn with retry suggestion

Context alternation is maintained by the context layer (append_assistant inserts
synthetic user bridges), so no reset is needed to prevent OpenAI violations.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import TYPE_CHECKING

from agent_console import format_duration_ms, loop_warning, tool_start
from agent_context import (
    TauContext,
)
from agent_loop_detect import LoopDetector
from agent_message_utils import get_last_real_user_prompt
from agent_reflection import ReflectionScheduler

if TYPE_CHECKING:
    from agent_core import TauErgon


class LoopEscalationManager:
    """Manage loop detection escalation, reflection injection, and recovery.

    Encapsulates the loop escalation logic previously embedded in TauErgon:
    - Escalation handling (levels 1-4)
    - Recovery from invalid end-of-turn states
    - Periodic reflection injection

    Attributes:
        loop_detector: LoopDetector instance for pattern detection.
        reflection_scheduler: ReflectionScheduler for adaptive reflection timing.
        context: TauContext instance for context manipulation.
        agent: Parent TauErgon reference for agent state access.
    """

    def __init__(
        self,
        loop_detector: LoopDetector,
        reflection_scheduler: ReflectionScheduler,
        context: TauContext,
        agent: TauErgon,
    ):
        """Initialize the loop escalation manager.

        Args:
            loop_detector: LoopDetector instance for pattern detection.
            reflection_scheduler: ReflectionScheduler for adaptive reflection timing.
            context: TauContext instance for context manipulation.
            agent: Parent TauErgon reference for agent state access.
        """
        self._loop_detector = loop_detector
        self._reflection_scheduler = reflection_scheduler
        self._context = context
        self._agent = agent

    def set_reflection_scheduler(self, scheduler: ReflectionScheduler) -> None:
        """Replace the reflection scheduler (e.g., when switching LLM groups)."""
        self._reflection_scheduler = scheduler

    def handle_loop_escalation(self) -> bool:
        """Handle loop escalation based on total_warnings count.

        New 5-level escalation system with text cycling:
        - Level 1 (warnings 3-5): Alert warnings prepended to tool output
        - Level 2 (warnings 6-8): Simulated self-reflection via synthetic think calls
        - Level 3 (warnings 9-11): Guided introspection with structured user questions
        - Level 4 (warnings 12-14): Forced analysis with deep introspection
        - Level 5 (warnings 15+): Termination — force_end_turn with retry suggestion

        For T (think) and K (skill) nesting types, escalation is immediate:
        at Level 1 (3 warnings), the turn is terminated using the last substantive
        response instead of going through the full escalation ladder.

        Each level fires exactly 3 times with different, escalating texts.

        Returns:
            True if the loop should continue, False if turn should end.
        """
        info = self._loop_detector.get_escalation_info()
        total = info["total_warnings"]
        level = info["escalation_level"]

        # For T (think) and K (skill) nesting types, abort immediately at Level 1
        # using the last substantive response instead of the full escalation ladder.
        if level >= 1 and self._agent._is_restricted_nesting():
            self._agent.force_end_turn = (
                f"Loop detected ({total} warnings) — terminating with last response."
            )
            loop_warning(4, f"Turn terminated (restricted nesting): {total} loop warnings")
            return False

        if level >= 5:
            # Termination: force end of turn with retry suggestion
            self._agent.force_end_turn = self._format_termination_message(info)
            loop_warning(4, f"Turn terminated: {total} loop warnings")
            return False

        if level == 4:
            # Forced analysis: synthetic assistant + think result
            assistant_text, think_result = self._get_level4_text(total, info)
            self._inject_assistant_tool(assistant_text, think_result)
            loop_warning(3, f"Forced analysis: {total} warnings")
            return True

        if level == 3:
            # Guided introspection: synthetic assistant + user questions
            assistant_text, user_text = self._get_level3_text(total, info)
            self._inject_assistant_user(assistant_text, user_text)
            loop_warning(3, f"Guided introspection: {total} warnings")
            return True

        if level == 2:
            # Simulated self-reflection: synthetic assistant + think result
            assistant_text, think_result = self._get_level2_text(total, info)
            self._inject_assistant_tool(assistant_text, think_result)
            loop_warning(2, f"Self-reflection: {total} warnings")
            return True

        if level == 1:
            # Alert only — loop_prefix in agent_tool_executor handles tool output prepend
            loop_warning(1, f"Possible loop: {total} warnings")
            return True

        return True

    # ── Text cycling helpers ────────────────────────────────────────────

    def _text_index(self, total_warnings: int, level_start: int) -> int:
        """Get text index (0, 1, 2) for a given warning count within a level."""
        return (total_warnings - level_start) % 3

    # ── Level 2 texts (warnings 6-8): Simulated self-reflection ─────────

    def _get_level2_text(self, total_warnings: int, info: dict) -> tuple[str, str]:
        """Get level 2 text pair: (assistant_text, think_result)."""
        idx = self._text_index(total_warnings, 6)

        texts = [
            # Warning 6
            (
                "I notice I'm repeating the same tool call. Let me pause and consider whether this approach is actually productive, or if I need to step back and reassess what I'm trying to accomplish here.",
                "Reflection: I've been calling the same tool repeatedly. Key questions — am I getting genuinely new information each time, or am I spinning in place? What have I learned so far from these calls? Is there a different tool or a different set of arguments that would give me the insight I need? I should verify my progress before continuing.",
            ),
            # Warning 7
            (
                "I'm clearly stuck in a repetitive pattern. The same tool call isn't yielding new results. I need to step back, reassess my overall strategy for this task, and consider whether my fundamental approach is correct before I make another call.",
                "Deeper analysis: Multiple repeated calls strongly suggest I'm not making progress. I need to answer these questions honestly: (1) What was my original goal for this sequence of calls? (2) What information have I actually gathered that I didn't already know? (3) Why isn't the same call working — is it the wrong tool, wrong arguments, or am I misunderstanding the task? (4) What is a concretely different approach I could take right now? I should try something different, not repeat.",
            ),
            # Warning 8
            (
                "This repetition is no longer productive at all. I'm going to fundamentally rethink my entire approach to this task. Continuing the same pattern will not resolve the situation, and I need to make a deliberate change in direction before proceeding further.",
                "Critical reassessment: I'm trapped in a loop and the same tool call is not breaking it. I need to do three things: First, summarize everything I know from all these repeated calls — what is the actual state of knowledge? Second, identify precisely what I'm still missing that's blocking progress. Third, determine whether a completely different tool, a different strategy, or even a text response (not a tool call) is what's actually needed right now. Continuing this pattern will absolutely not help. I must change course.",
            ),
        ]
        return texts[idx]

    # ── Level 3 texts (warnings 9-11): Guided introspection ──────────────

    def _get_level3_text(self, total_warnings: int, info: dict) -> tuple[str, str]:
        """Get level 3 text pair: (assistant_text, user_text)."""
        idx = self._text_index(total_warnings, 9)
        last_real = get_last_real_user_prompt(self._context.get_messages())
        n = info["total_warnings"]

        texts = [
            # Warning 9
            (
                "I'm repeating myself and I'm not making meaningful progress. I need to stop, assess where I am, and figure out what I should be doing differently before I call any more tools.",
                f"Your original task was:\n\n{last_real}\n\nBefore you continue with any tool calls, please answer these questions as plain text:\n\n1. What have you done so far this turn?\n2. What have you learned from your tool calls?\n3. What do you still need to do to complete the task?\n4. What is the immediate next step — and what specific tool call (if any) would accomplish it?\n\nImportant: Do not repeat the same tool call you've been using. Choose something different, or provide a text response if that's more appropriate.",
            ),
            # Warning 10
            (
                "I'm trapped in a loop. I've been calling the same tool over and over without breaking the pattern. I've tried continuing but it's not working. I need help reconsidering my approach from scratch.",
                f"STOP. You have received {n} loop warnings this turn. Your original task:\n\n{last_real}\n\nAnswer these questions as text — do not make any tool calls until you've answered all five:\n\n1. Summarize every distinct action you've taken this turn (in order)\n2. What information have you actually gathered that was new?\n3. Why is the same tool call not working — what's the root cause?\n4. What is a DIFFERENT approach you could take that you haven't tried yet?\n5. What specific tool call (NOT the one you've been repeating) should you make next, or should you provide a text answer?\n\nYou must answer all 5 questions before making any tool calls.",
            ),
            # Warning 11
            (
                "I cannot break this pattern on my own. I'm going in circles despite multiple warnings. I need to completely restart my thinking about this task and get external guidance on what to do next.",
                f"CRITICAL: You are in a confirmed loop ({n} warnings). Continuing the same pattern will NOT resolve this — it has been tried multiple times and failed.\n\nYour original task:\n\n{last_real}\n\nI need you to do something you haven't done yet — answer these questions thoroughly as text:\n\n1. List EVERY tool you've called this turn (in order, with arguments)\n2. For each tool call, what did it give you that you didn't already know?\n3. Be honest: how many of those calls were redundant or provided no new information?\n4. What is the ONE thing you still don't know that's blocking progress?\n5. What tool (NOT the one you've been repeating) would answer that question? Or do you have enough information to answer the original task as text?\n\nAnswer as text. Then act on your answer with a DIFFERENT tool or a text response.",
            ),
        ]
        return texts[idx]

    # ── Level 4 texts (warnings 12-14): Forced analysis ──────────────────

    def _get_level4_text(self, total_warnings: int, info: dict) -> tuple[str, str]:
        """Get level 4 text pair: (assistant_text, think_result)."""
        idx = self._text_index(total_warnings, 12)
        n = info["total_warnings"]

        texts = [
            # Warning 12
            (
                "I'm deeply stuck in a loop and standard self-correction isn't working. I need to do a thorough, structured analysis of my entire situation — what I know, what I don't know, and how to get unstuck.",
                "Structured analysis — I am stuck repeating the same tool call. From memory, I need to answer these questions without using any tools:\n\n(1) What was the original task assigned to me?\n(2) What actions have I taken so far, and in what order?\n(3) What did I learn from those actions — what facts do I now have?\n(4) What is left to do to complete the task?\n(5) What is the immediate next step — a specific tool call different from the one I've been repeating, or a text response?\n\nI must not use any tools during this analysis. I must answer from memory and reasoning alone. The goal is to break the loop by identifying what I actually need to do next.",
            ),
            # Warning 13
            (
                "Every attempt to continue has led back to the same tool call. I suspect my fundamental understanding of the task may be incorrect. I need to examine whether I'm even approaching this problem the right way, not just what tool to use next.",
                "Deep introspection — I suspect my approach to this task is fundamentally wrong. I need to analyze the root cause, not just the symptoms:\n\n(1) What did I think the task required when I started?\n(2) What am I actually doing right now, and how does it differ from my original plan?\n(3) Where is the mismatch — did I misunderstand the task, or did the situation change?\n(4) If I were starting this task from scratch right now, with everything I know, what would my first step be?\n(5) What should I do NOW to get back on track — and is it a tool call, a text response, or something else entirely?\n\nDo not use tools. Pure reasoning only. I need to identify the fundamental error in my approach, not just try a different tool.",
            ),
            # Warning 14
            (
                "I have exhausted this approach completely. I am going to abandon my current strategy entirely and start fresh with a completely new perspective on what needs to be done. This is my last attempt to break the loop before the turn is terminated.",
                f"FINAL ANALYSIS BEFORE TURN TERMINATION — I have been in a loop for {n} warnings and all previous interventions have failed. I need to be completely honest:\n\n(1) What was I trying to achieve with the repeated tool calls?\n(2) Why did it fail — what is the specific reason it didn't work?\n(3) What did I misunderstand about the task, the tool, or the situation?\n(4) If I were starting this task from scratch right now, what would I do differently in my first step?\n(5) What is the single most important thing I need to do next to make progress — and is it realistic that it will work?\n\nDo not use tools. This is my last reasoning pass before the turn ends. I need to identify the exact blockage and the exact action to resolve it. If I cannot identify a path forward, I should provide a text response explaining what I know and what's blocking me.",
            ),
        ]
        return texts[idx]

    # ── Level 5: Termination message ─────────────────────────────────────

    def _format_termination_message(self, info: dict) -> str:
        """Format the termination message for warning 15+."""
        last_real = get_last_real_user_prompt(self._context.get_messages())
        n = info["total_warnings"]
        tool_warnings = info.get("tool_warnings", {})
        most_repeated = max(tool_warnings, key=tool_warnings.get) if tool_warnings else "unknown"
        repeat_count = tool_warnings.get(most_repeated, 0) if tool_warnings else 0

        return (
            f"TURN TERMINATED: Loop detection forced end of turn after {n} warnings.\n\n"
            f"Summary: The agent repeated '{most_repeated}' {repeat_count} times without progress. "
            f"12 escalation interventions were attempted across 4 levels:\n"
            f"  - Level 1 (warnings 3-5): Alert warnings prepended to tool output\n"
            f"  - Level 2 (warnings 6-8): Simulated self-reflection via synthetic think calls\n"
            f"  - Level 3 (warnings 9-11): Guided introspection with structured questions\n"
            f"  - Level 4 (warnings 12-14): Forced analysis with deep introspection\n\n"
            f"None of these interventions broke the loop. The turn is being terminated.\n\n"
            f"Suggestion: Retry the original task. The conversation history now contains "
            f"extensive analysis of what went wrong, including multiple self-reflections, "
            f"structured assessments, and forced analysis passes. Use this context to "
            f"avoid repeating the same pattern.\n\n"
            f"Original task: {last_real}\n"
            f"Most-repeated tool: {most_repeated} (called {repeat_count} times consecutively)"
        )

    # ── Injection helpers ────────────────────────────────────────────────

    def _inject_assistant_tool(self, assistant_text: str, tool_result: str) -> None:
        """Inject a synthetic assistant message with a think() tool call and result.

        Maintains OpenAI alternation: context ends with tool result, which is valid
        for the next LLM call.
        """
        tool_call_id = f"call_{uuid.uuid4().hex[:24]}"
        self._context.append_assistant(
            assistant_text,
            tool_calls=[{
                "id": tool_call_id,
                "type": "function",
                "function": {"name": "think", "arguments": "{}"},
            }],
            synthetic=True,
        )
        self._context.append_tool(tool_result, tool_call_id)

    def _inject_assistant_user(self, assistant_text: str, user_text: str) -> None:
        """Inject a synthetic assistant message followed by a synthetic user message.

        Maintains OpenAI alternation: context ends with user message, which is valid
        for the next LLM call.
        """
        self._context.append_assistant(assistant_text, synthetic=True)
        self._context.append_synthetic_user("escalation", user_text)

    def recover_from_invalid_end_of_turn(
        self,
        response_text: str,
        reasoning_content: str | None,
    ) -> None:
        """Recover from invalid end-of-turn by injecting a synthetic bridge message.

        Uses the same synthetic bridge pattern as append_assistant() auto-bridges.
        This maintains consistent context alternation across all recovery paths.

        Args:
            response_text: The defective assistant response text.
            reasoning_content: The reasoning content (if any).
        """
        # Get the last REAL user prompt (not synthetic escalation messages)
        last_real_prompt = get_last_real_user_prompt(self._context.get_messages())

        # Build recovery instructions
        recovery_text = (
            "Your previous response was structurally incomplete "
            "(truncated, unclosed tags, or malformed). "
            "Please complete your response properly. "
            "When done, respond with your final answer."
        )

        # Get the last real user prompt to provide context
        synthetic_content = f"{recovery_text}\n\nOriginal prompt for this turn:\n{last_real_prompt}"

        # Append synthetic user with bridge - maintains alternation compliance
        # Context may end with tool results or assistant response; bridge helper handles both
        self._context.append_synthetic_user_with_bridge("recovery", synthetic_content)

    # ── Reflection injection ────────────────────────────────────────────

    def _inject_think_reflection(
        self,
        question: str,
        id_prefix: str,
        concise_summary: str,
        console_label: str,
        console_desc: str,
        track_timing: bool = False,
    ) -> None:
        """Inject a synthetic think tool call for reflection.

        Shared implementation for inject_early_reflection and inject_reflection.

        Args:
            question: The reflection question to pass to think tool.
            id_prefix: Prefix for the synthetic tool_call_id.
            concise_summary: Summary text for the assistant message.
            console_label: Label for console display (e.g., "think [early-reflect]").
            console_desc: Description for console display.
            track_timing: If True, measure elapsed time and include in error messages.
        """
        from agent_tool_executor import execute_tool_call

        tool_call_id = f"{id_prefix}{uuid.uuid4().hex[:8]}"

        synthetic_tc = {
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": "think",
                "arguments": json.dumps({"question": question}),
            },
        }

        self._context.append_assistant(
            concise_summary,
            [synthetic_tc],
            synthetic=True,
        )

        tool_start(console_label, console_desc)

        try:
            start = time.monotonic() if track_timing else None
            result = execute_tool_call(
                {"id": tool_call_id, "name": "think", "args_dict": {"question": question}},
                self._agent,
                system_call=True,
                bypass_filter=True,
            )
        except Exception as e:
            if track_timing and start is not None:
                elapsed = time.monotonic() - start
                result = (
                    f"[Reflection failed after {format_duration_ms(elapsed * 1000)}: "
                    f"{type(e).__name__}: {str(e)[:200]}]"
                )
            else:
                result = f"[Early reflection failed: {type(e).__name__}: {str(e)[:200]}]"
        finally:
            if track_timing:
                self._reflection_scheduler.mark_reflection_done()
        self._context.append_tool(result, tool_call_id)

    def inject_early_reflection(self, question: str | None = None) -> None:
        """Inject an entry microplan reflection BEFORE the first LLM call.

        Unlike periodic reflection, this runs at loop entry to give the agent
        a chance to plan before acting. Uses a task-focused prompt.
        """
        last_real_prompt = get_last_real_user_prompt(self._context.get_messages())

        if question is None:
            question = (
                f"(1) What is our goal? "
                f"(2) What does the user want: {last_real_prompt}? "
                f"(3) What is the high-level plan to accomplish this? "
                f"(4) What tools will likely be needed? "
                "Be concise — 3 to 5 sentences max."
            )

        self._inject_think_reflection(
            question=question,
            id_prefix="early_reflect_",
            concise_summary="Entry reflection completed.",
            console_label="think [early-reflect]",
            console_desc="entry microplan — system-initiated",
            track_timing=False,
        )

    def inject_reflection(self, question: str | None = None) -> None:
        """Inject a periodic reflection into the tool loop.

        Uses a decoupled approach:
        - Fork receives the FULL last real user prompt (rich context for thinking)
        - Main context receives a CONCISE summary (reduces pollution)

        Args:
            question: Optional custom reflection question. If None, uses default
                reflection prompt based on the last real user input.
        """
        # Get the last REAL user prompt (not synthetic escalation messages)
        last_real_prompt = get_last_real_user_prompt(self._context.get_messages())

        # Build the reflection question
        if question is None:
            question = (
                f"(1) What is our goal? "
                f"(2) What have we accomplished so far? "
                f"(3) Are we on track for: {last_real_prompt}? "
                f"(4) What are the next 2-3 steps? "
                "Be concise — 3 to 5 sentences max."
            )

        self._inject_think_reflection(
            question=question,
            id_prefix="reflect_",
            concise_summary="Reflection completed.",
            console_label="think [auto-reflect]",
            console_desc="periodic reflection — system-initiated",
            track_timing=True,
        )
