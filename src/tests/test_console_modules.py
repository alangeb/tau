"""Smoke tests for console modules — verifies all exports are importable and callable.

After splitting agent_console into focused modules, this module ensures:
1. Each module imports cleanly (no circular imports, no missing dependencies)
2. Every public name in __all__ is callable (no broken references)
"""

import pytest


MODULES = [
    "agent_console_primitives",
    "agent_console_messages",
    "agent_console_display",
    "agent_console",
    "agent_console_audit",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_module_imports_cleanly(module_name):
    """Each console domain module imports without errors."""
    __import__(module_name)


@pytest.mark.parametrize("module_name", MODULES)
def test_all_public_exports_are_callable(module_name):
    """Every public name in __all__ is callable (function/method, not a constant)."""
    mod = __import__(module_name)
    for name in getattr(mod, "__all__", []):
        # Skip private names (underscore prefix) — they may be internal state
        if name.startswith("_"):
            continue
        obj = getattr(mod, name, None)
        if obj is not None:
            assert callable(obj), f"{module_name}.{name} is in __all__ but not callable"


def test_primitives_has_core_functions():
    """Verify agent_console_primitives exports the foundation functions."""
    import agent_console_primitives as p
    assert callable(p.echo)
    assert callable(p.blank_line)
    assert callable(p.status)
    assert callable(p.reasoning)
    assert callable(p.verbose)


def test_console_has_error_functions():
    """Verify agent_console exports error/warning functions."""
    import agent_console as c
    assert callable(c.error)
    assert callable(c.warning)
    assert callable(c.error_display)


def test_console_has_message_functions():
    """Verify agent_console exports message display functions."""
    import agent_console as c
    assert callable(c.assistant_message_display)
    assert callable(c.user_echo)
    assert callable(c.undo_message)


def test_console_has_flow_functions():
    """Verify agent_console exports flow control functions."""
    import agent_console as c
    assert callable(c.restart_flow)
    assert callable(c.interrupted_message)
    assert callable(c.force_exit_message)


def test_console_has_llm_functions():
    """Verify agent_console exports LLM status functions."""
    import agent_console as c
    assert callable(c.llm_timeout_message)
    assert callable(c.llm_validation_retry)


def test_console_has_loop_functions():
    """Verify agent_console exports loop warning functions."""
    import agent_console as c
    assert callable(c.loop_warning_display)
    assert callable(c.loop_warning)


def test_console_has_subagent_functions():
    """Verify agent_console exports subagent/fork functions."""
    import agent_console as c
    assert callable(c.subagent_start_display)
    assert callable(c.fork_display)
    assert callable(c.subagent_output_header)


def test_console_has_agent_functions():
    """Verify agent_console exports A2A/agent functions."""
    import agent_console as c
    assert callable(c.agents_table_header)
    assert callable(c.agent_status_message)
    assert callable(c.a2a_started_message)


def test_console_has_compression_functions():
    """Verify agent_console exports compression functions."""
    import agent_console as c
    assert callable(c.compress_success)
    assert callable(c.compress_fail)
    assert callable(c.compression_step_summary)


def test_console_has_context_functions():
    """Verify agent_console exports context display functions."""
    import agent_console as c
    assert callable(c.context_dump)
    assert callable(c.context_restored)
    assert callable(c.context_status_bar)


def test_console_has_status_functions():
    """Verify agent_console exports status display functions."""
    import agent_console as c
    assert callable(c.agent_status)
    assert callable(c.print_agent_exit_summary)


def test_console_has_help_functions():
    """Verify agent_console exports help display functions."""
    import agent_console as c
    assert callable(c.show_help)
    assert callable(c.show_commands)
    assert callable(c.show_tools)


def test_console_has_tool_functions():
    """Verify agent_console exports tool display functions."""
    import agent_console as c
    assert callable(c.tool_start)
    assert callable(c.tool_result)
    assert callable(c.tool_output)
