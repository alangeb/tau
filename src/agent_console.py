"""Consolidated console display module for TauErgon.

This is the single entry point for all console functionality. Uses lazy
loading via __getattr__ to re-export everything from:
  - agent_console_primitives.py  (low-level I/O primitives)
  - agent_console_messages.py    (declarative message templates)
  - agent_console_display.py     (complex display functions)

agent_console_audit.py remains separate (complex audit parsing logic).

Adding a function to a sub-module's __all__ is the ONLY change needed —
no edits to this facade are required.
"""
from __future__ import annotations

# ── Sub-modules (imported lazily on first attribute access) ──────────────────
_CONSOLE_MODULES = (
    "agent_console_primitives",
    "agent_console_messages",
    "agent_console_display",
)


def __getattr__(name: str) -> object:
    """Lazy-load attributes from sub-modules.

    Looks up `name` in each sub-module's __all__ and returns the first match.
    Caches the result in this module's globals so subsequent accesses are fast.
    """
    import importlib  # lazy import to avoid cost at module load time

    for mod_name in _CONSOLE_MODULES:
        mod = importlib.import_module(mod_name)
        if name in getattr(mod, "__all__", ()):
            val = getattr(mod, name)
            globals()[name] = val  # cache for next access
            return val

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Return all exported names so tab-completion and introspection work."""
    return list(__all__)


# ── __all__ exports (dynamic composition — single source of truth) ───────────
# Composed from sub-module __all__ lists. Adding a function requires editing
# only the originating module's __all__, not this facade.

def _build_all() -> list[str]:
    """Build __all__ from sub-module __all__ lists, deduplicating."""
    import importlib
    seen: set[str] = set()
    result: list[str] = []
    for mod_name in _CONSOLE_MODULES:
        mod = importlib.import_module(mod_name)
        for name in getattr(mod, "__all__", []):
            if name not in seen:
                seen.add(name)
                result.append(name)
    return result


__all__ = _build_all()