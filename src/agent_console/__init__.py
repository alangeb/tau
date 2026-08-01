"""Agent console package for TauErgon.

Provides focused submodules for console display functions:
- audit: Console-to-audit bridging (_log_audit)
- audit_display: Audit log viewer (AuditRecord, parse_audit_file, show_audit)
- primitives: Low-level I/O (echo, status, _cw, prompt, etc.)
- messages: MessageRegistry, _ConsoleMessage class, and all message definitions
- display: All display functions (tool, command, status, context, llm, simple, loop)

Uses lazy loading via __getattr__ to avoid importing all submodules at package
load time. This eliminates the maintenance burden of keeping explicit re-exports
in sync with submodule changes and makes the dependency graph acyclic.

Symbols are resolved on first access from their source submodules.
Backward compatible: `from agent_console import X` works exactly as before.
"""
from __future__ import annotations

import importlib as _importlib

# ── Lazy loading configuration ─────────────────────────────────────────────────
# Maps submodule names to the symbols they export.
# Submodules are the source of truth — add symbols to submodule __all__, not here.
_SUBMODULES: dict[str, str] = {
    "audit": "agent_console.audit",
    "audit_display": "agent_console.audit_display",
    "primitives": "agent_console.primitives",
    "messages": "agent_console.messages",
    "display": "agent_console.display",
}

# Cache for resolved symbols (avoids repeated imports)
_attr_cache: dict[str, object] = {}


def __getattr__(name: str) -> object:
    """Lazily resolve symbols from submodules on first access.

    This replaces the explicit re-export pattern that required maintaining
    a large __all__ list and importing all submodules at package load time.

    Resolution order:
    1. Check cache (already resolved)
    2. Iterate submodules, import from first one that has the symbol
    3. Raise AttributeError if not found

    Args:
        name: The attribute name to resolve.

    Returns:
        The resolved symbol from the appropriate submodule.

    Raises:
        AttributeError: If the symbol is not found in any submodule.
    """
    # Check cache first
    if name in _attr_cache:
        return _attr_cache[name]

    # Try each submodule in order
    for submodule_name, module_path in _SUBMODULES.items():
        try:
            module = _importlib.import_module(module_path)
            if hasattr(module, name):
                value = getattr(module, name)
                _attr_cache[name] = value
                return value
        except ImportError:
            continue

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Return all resolvable symbols for IDE autocomplete and dir() support.

    Aggregates __all__ from all submodules plus standard dunder attributes.
    """
    result = sorted(name for name in globals() if name.startswith("__"))
    for _, module_path in _SUBMODULES.items():
        try:
            module = _importlib.import_module(module_path)
            result.extend(getattr(module, "__all__", []))
        except ImportError:
            continue
    return result


# Build __all__ dynamically from submodule __all__ lists.
# This is evaluated at module load time and cached.
def _build_all() -> list[str]:
    """Build __all__ by aggregating __all__ from all submodules."""
    all_symbols: list[str] = []
    for _, module_path in _SUBMODULES.items():
        try:
            module = _importlib.import_module(module_path)
            all_symbols.extend(getattr(module, "__all__", []))
        except ImportError:
            continue
    return all_symbols


__all__ = _build_all()


# Note: Internal symbols (_cw, _ConsoleMessage, _msg) are available via
# lazy loading but are implementation details for use by messages.py and
# display.py only. They are not part of the public API.
