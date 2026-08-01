"""Signal end of turn with a final message.

Sets ``force_end_turn`` to cause the main loop to append the result and
return immediately.

When message is empty or whitespace-only, resolves to the last substantive
assistant message so the model doesn't have to repeat itself. Raises
ValueError if no substantive response was tracked — forces the model to
provide a real message on retry.

The ``end_turn`` tool MUST be the only tool call in an assistant message.
If mixed with other tool calls, the other tools execute but ``end_turn``
is silently filtered out (the turn does NOT end).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from tools import ToolMetadata

if TYPE_CHECKING:
    from agent_core import TauErgon


# ── Tool metadata ────────────────────────────────────────────────────────────

metadata = ToolMetadata(
    name="end_turn",
    description=(
        "Signal the end of the current turn and provide a final message. "
        "MANDATORY: You MUST call this tool to end every turn. "
        "Only call end_turn when you are finished — you will not be able to continue afterwards. "
        "end_turn MUST be the only tool call in an assistant message. "
        "Plain text responses without end_turn will NOT end the turn. "
        "To end the turn, call the end_turn tool with the message parameter. "
        "If omitted or empty, your last substantive assistant message is used as the "
        "final response, or pass your final response directly."
    ),
    aliases_arg={"text": "message", "response": "message", "result": "message"},
    max_size=8192,
)


# ── Args schema ──────────────────────────────────────────────────────────────

@dataclass
class Args:
    """Arguments for the end_turn tool."""
    message: str = field(
        default="",
        metadata={
            "description": (
                "The final message to append as the last assistant output "
                "when the turn ends. If omitted or empty, the system uses "
                "your last substantive assistant message as the final response. "
                "Only call end_turn when you are finished — you will not be "
                "able to continue afterwards."
            )
        }
    )


# ── Execution ────────────────────────────────────────────────────────────────

def run(
    message: str = "",
    agent: "TauErgon | None" = None,
    tool_call_id: str | None = None,
) -> str:
    """End the current turn immediately by setting ``force_end_turn``.

    When message is empty or whitespace-only, resolves to the
    last substantive assistant message so the model doesn't have to repeat itself.
    Raises ValueError if no substantive response was tracked — forces the model to
    provide a real message on retry.
    """
    stripped = message.strip() if message else ""

    if not stripped:
        # Empty string → resolve to last substantive response.
        if agent and agent.last_substantive_response:
            resolved = agent.last_substantive_response
            agent.force_end_turn = resolved
            return resolved
        else:
            raise ValueError(
                "end_turn called without a message and no substantive assistant "
                "response was tracked. Provide a message after "
                "producing a substantive response."
            )
    else:
        if agent:
            agent.force_end_turn = stripped
        return stripped