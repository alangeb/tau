"""Subsystem initialization for TauErgon.

Encapsulates the creation and wiring of all agent subsystems:
session manager, loop detector, reflection scheduler, loop escalation
manager, EOT protection, heartbeat manager, and input handler.

This module reduces the import burden on agent_core.py and makes
subsystem initialization testable in isolation.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from agent_commands import CommandManager
from agent_console import warning
from agent_console.templates import register_console_messages
from agent_eot_protection import EOTProtection
from agent_heartbeat import HeartbeatManager
from agent_loop_detect import LoopDetector
from agent_loop_escalation import LoopEscalationManager
from agent_reflection import ReflectionScheduler
from agent_session import AgentSessionManager
from tools import TOOLS

if TYPE_CHECKING:
    from agent_core import TauErgon


@dataclass
class SubsystemBundle:
    """Bundle of initialized subsystems returned by init_subsystems().

    Contains ONLY the subsystem instances that TauErgon needs after
    initialization. State variables and None placeholders are NOT included
    — they are initialized directly in _init_subsystems() as assignments.
    """
    # Session management
    session: AgentSessionManager

    # Loop detection and escalation
    loop_detector: LoopDetector
    reflection_scheduler: ReflectionScheduler
    loop_escalation: LoopEscalationManager

    # EOT protection
    eot_protection: EOTProtection

    # Heartbeat (idle detection)
    heartbeat: HeartbeatManager

    # Commands / tools
    available_tool_names: list[str]


def init_subsystems(
    agent: TauErgon,
    init: "AgentInitConfig",
) -> SubsystemBundle:
    """Initialize all agent subsystems and return a bundle.

    This function encapsulates the creation and wiring of all subsystems
    that TauErgon needs. It is called once from TauErgon.__init__() after
    config resolution.

    Args:
        agent: The TauErgon instance being initialized.
        init: The resolved AgentInitConfig with all settings.

    Returns:
        SubsystemBundle containing only the subsystem instances.
        State variables and None placeholders are NOT included — they are
        initialized directly in _init_subsystems() as assignments.
    """
    # Session management (token tracking, context/audit file paths)
    session = AgentSessionManager()

    # Loop detection (sliding-window pattern matching)
    loop_detector = LoopDetector(
        window_size=init.loop_detection_window_size,
        repeat_threshold=init.loop_detection_repeat_threshold,
        replace_unknown_tools=init.loop_detection_replace_unknown_tools,
    )

    # Reflection scheduler (periodic self-reflection triggers)
    reflection_scheduler = ReflectionScheduler(
        init.reflection_config,
    )

    # Loop escalation (reactive recovery from detected loops)
    loop_escalation = LoopEscalationManager(
        loop_detector=loop_detector,
        reflection_scheduler=reflection_scheduler,
        context=agent.context,
        agent=agent,
    )

    # Audit writer initialization
    session.init_audit_writer()

    # EOT protection (needs audit_writer, so initialized after session)
    eot_protection = EOTProtection(agent)

    # Register console message callbacks (audit bridge wiring)
    register_console_messages()

    # Command / tool registration
    available_tool_names = list(TOOLS.keys())

    # Check for .py/.md command conflicts at startup
    _check_command_conflicts()

    # Heartbeat (idle detection and auto-task execution)
    heartbeat = HeartbeatManager(
        enabled=init.heartbeat_enabled,
        interval_seconds=init.heartbeat_interval,
        agent=agent,
    )

    return SubsystemBundle(
        session=session,
        loop_detector=loop_detector,
        reflection_scheduler=reflection_scheduler,
        loop_escalation=loop_escalation,
        eot_protection=eot_protection,
        heartbeat=heartbeat,
        available_tool_names=available_tool_names,
    )


def _check_command_conflicts() -> None:
    """Check for .py/.md command conflicts at startup and warn."""
    conflicts = CommandManager._get_registry().find_conflicts()
    if conflicts:
        for name in conflicts:
            warning(
                f"Command '{name}' exists as both .py and .md — .py takes precedence"
            )


def read_system_prompt() -> str:
    """Read and format the system prompt from AGENT.md.

    Computes default audit/context file paths internally using
    _get_log_filename_prefix() and LOG_DIR. No session object needed.

    Returns:
        The formatted system prompt string.
    """
    from agent_core import _safe_format_template
    from agent_session import LOG_DIR, _get_log_filename_prefix

    prefix = _get_log_filename_prefix()
    audit_file = Path(LOG_DIR) / f"{prefix}.audit"
    context_file = Path(LOG_DIR) / f"{prefix}.context"

    agent_path = Path(__file__).resolve().parent / "AGENT.md"
    system_prompt = "You are helpful AI assistant. Do what User asks."
    if agent_path.exists():
        try:
            raw = agent_path.read_text().strip()
            system_prompt = _safe_format_template(
                raw,
                log_file=str(audit_file),
                audit_file=str(audit_file),
                context_file=str(context_file),
            )
        except OSError as exc:
            print(f"WARNING: Could not read AGENT.md: {exc}", file=sys.stderr)

    return system_prompt


__all__ = [
    "SubsystemBundle",
    "init_subsystems",
    "read_system_prompt",
]