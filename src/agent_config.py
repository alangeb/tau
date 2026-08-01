"""Configuration management for TauErgon — dataclasses, file/env loading."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from agent_llm_models import DEFAULT_MAX_CONTEXT_TOKENS

__all__ = [
    "MalformedConfig",
    "LoopDetectionConfig",
    "NestingConfig",
    "ToolExecutionConfig",
    "DelegateConfig",
    "ExternalServicesConfig",
    "PathSecurityConfig",
    "WikiConfig",
    "LLMGroup",
    "Config",
    "get_config",
    "reset_config_cache",
]


# ---------------------------------------------------------------------------
# Nested config dataclasses (frozen, immutable defaults)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MalformedConfig:
    """Retry limits for malformed LLM responses."""
    silent_retries: int = 4
    enhanced_retries: int = 7
    explicit_retries: int = 10


@dataclass(frozen=True)
class LoopDetectionConfig:
    """Sliding-window loop detection parameters."""
    window_size: int = 30
    repeat_threshold: int = 3
    replace_unknown_tools: int = 0  # 0=off, N=replace on Nth attempt


@dataclass(frozen=True)
class NestingConfig:
    """Nesting depth restrictions."""
    depth_threshold: int = 2


@dataclass(frozen=True)
class ToolExecutionConfig:
    """Tool execution timeouts and polling."""
    poll_interval: float = 0.5
    default_timeout: int = 180
    long_running_timeout: int = 86400


@dataclass(frozen=True)
class DelegateConfig:
    """Delegate mode parameters."""
    max_iterations: int = 30
    warning_at: int = 25


@dataclass(frozen=True)
class ReflectionConfig:
    """Periodic reflection scheduler parameters."""
    enabled: bool = True
    initial_think: bool = True
    min_interval: int = 15
    max_interval: int = 30
    content_threshold_bytes: int = 200
    reactive_on_loop_warning: bool = True
    reactive_on_error_burst: bool = True


@dataclass(frozen=True)
class ExternalServicesConfig:
    """External service URLs (empty = disabled)."""
    searxng_url: str = ""
    crawl4ai_url: str = ""


@dataclass(frozen=True)
class PathSecurityConfig:
    """Configurable path whitelist for sandbox validation.

    Whitelisted paths bypass the double-call confirmation requirement for
    read operations, reducing friction for legitimate access to common
    directories like /tmp and the user's home directory.

    Security: Whitelist is ADDITIVE — it never weakens double-call
    confirmation for write operations. Symlinks are resolved before
    checking to prevent traversal attacks.
    """
    allowed_paths: list[str] = field(
        default_factory=lambda: ["/tmp", os.path.expanduser("~")]
    )


@dataclass(frozen=True)
class WikiConfig:
    """Wiki storage location configuration."""
    path: str = field(default_factory=lambda: os.path.expanduser("~/.local/tau/wiki"))


@dataclass(frozen=True)
class LogCleanupConfig:
    """Log file cleanup and retention configuration.

    Controls how failed_request.json files are managed:
    - ``retention``: Number of recent files to keep per session prefix
    - ``compress_age_days``: Compress files older than this many days
    - ``enabled``: Whether automatic cleanup runs after each failed request
    """
    retention: int = 5
    compress_age_days: int = 7
    enabled: bool = True


@dataclass(frozen=True)
class LogRetentionConfig:
    """Log rotation and archival configuration.

    Controls how session files are archived:
    - ``max_age_days``: Archive sessions older than this many days
    - ``max_size_mb``: Archive when log directory exceeds this size
    - ``archive_enabled``: Whether automatic archival is enabled
    - ``archive_dir``: Directory to archive sessions to
    """
    max_age_days: int = 30
    max_size_mb: int = 500
    archive_enabled: bool = True
    archive_dir: str = field(
        default_factory=lambda: os.path.expanduser("~/.local/tau/log/archive")
    )


@dataclass(frozen=True)
class LLMGroup:
    """Named LLM configuration with model, API, and generation parameters."""
    name: str
    model: str
    api_base: str
    api_key: str = ""
    timeout: int = 300
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    min_p: float | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    repetition_penalty: float | None = None
    chat_template_kwargs: dict[str, Any] | None = None
    reflection: "ReflectionConfig | None" = None


# ---------------------------------------------------------------------------
# Main Config class
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Config:
    """All tunable parameters for TauErgon.

    Resolution: tau.json → env vars → defaults.
    Active LLM group selected via llm_group_name (first group by default).
    """

    timeout: int = 180
    agent_name: str = "default"
    heartbeat_seconds: int | None = None
    debug: bool = False

    # Nested configs
    malformed: MalformedConfig = field(default_factory=MalformedConfig)
    loop_detection: LoopDetectionConfig = field(default_factory=LoopDetectionConfig)
    nesting: NestingConfig = field(default_factory=NestingConfig)
    delegate: DelegateConfig = field(default_factory=DelegateConfig)
    tool_execution: ToolExecutionConfig = field(default_factory=ToolExecutionConfig)
    reflection: ReflectionConfig = field(default_factory=ReflectionConfig)
    external_services: ExternalServicesConfig = field(default_factory=ExternalServicesConfig)
    path_security: PathSecurityConfig = field(default_factory=PathSecurityConfig)
    wiki: WikiConfig = field(default_factory=WikiConfig)
    log_cleanup: LogCleanupConfig = field(default_factory=LogCleanupConfig)
    log_retention: LogRetentionConfig = field(default_factory=LogRetentionConfig)

    # LLM inference parameters (forwarded directly to API, passthrough)
    inference_params: dict[str, Any] | None = None

    # LLM groups configuration
    llm_groups: dict[str, LLMGroup] | None = None
    llm_group_name: str | None = None

    # -----------------------------------------------------------------------
    # Environment variable mappings
    # Each entry: (env_var, config_key, optional_sub_key, converter)
    # sub_key is None for flat keys, present for nested keys.
    # -----------------------------------------------------------------------
    _ENV_OVERRIDES: ClassVar[tuple[tuple[str, str, str | None, Any], ...]] = (
        # Flat keys
        ("TAULLM", "llm_group_name", None, str),
        ("TAUTIMEOUT", "timeout", None, int),
        ("TAUERAGONNAME", "agent_name", None, str),
        ("TAU_HEARTBEAT", "heartbeat_seconds", None, int),
        # Nested keys
        ("TAU_MALFORMED_SILENT_RETRIES", "malformed", "silent_retries", int),
        ("TAU_MALFORMED_ENHANCED_RETRIES", "malformed", "enhanced_retries", int),
        ("TAU_MALFORMED_EXPLICIT_RETRIES", "malformed", "explicit_retries", int),
        ("TAU_LOOP_WINDOW", "loop_detection", "window_size", int),
        ("TAU_LOOP_REPEAT", "loop_detection", "repeat_threshold", int),
        ("TAU_NESTING_DEPTH", "nesting", "depth_threshold", int),
        ("TAU_TOOL_POLL_INTERVAL", "tool_execution", "poll_interval", float),
        ("TAU_TOOL_DEFAULT_TIMEOUT", "tool_execution", "default_timeout", int),
        ("TAU_TOOL_LONG_RUNNING_TIMEOUT", "tool_execution", "long_running_timeout", int),
        ("TAU_WIKI_DIR", "wiki", "path", str),
    )

    # Mapping of config keys to their nested dataclass types
    _NESTED_TYPES: ClassVar[dict[str, type]] = {
        "malformed": MalformedConfig,
        "loop_detection": LoopDetectionConfig,
        "nesting": NestingConfig,
        "delegate": DelegateConfig,
        "tool_execution": ToolExecutionConfig,
        "external_services": ExternalServicesConfig,
        "path_security": PathSecurityConfig,
        "reflection": ReflectionConfig,
        "wiki": WikiConfig,
        "log_cleanup": LogCleanupConfig,
        "log_retention": LogRetentionConfig,
    }

    @classmethod
    def _resolve_entry_dir(cls) -> Path:
        """Directory containing the entry script (tau.py)."""
        script = Path(sys.argv[0]).resolve()
        return script.parent if script.exists() else Path.cwd()

    @classmethod
    def _load_file_config(cls) -> dict[str, Any]:
        """Load tau.json from entry dir. Returns {} on missing/invalid file."""
        config_path = cls._resolve_entry_dir() / "tau.json"
        if not config_path.exists():
            return {}
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    @classmethod
    def _apply_env_overrides(cls, cfg_dict: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides to config dict."""
        for env_var, key, sub_key, converter in cls._ENV_OVERRIDES:
            env_val = os.getenv(env_var)
            if env_val is None:
                continue
            if sub_key is None:
                cfg_dict[key] = converter(env_val)
            else:
                cfg_dict.setdefault(key, {})[sub_key] = converter(env_val)
        return cfg_dict

    @classmethod
    def _merge_nested(cls, merged: dict[str, Any]) -> dict[str, Any]:
        """Convert nested dicts to dataclass instances and LLMGroup objects."""
        for key, cls_type in cls._NESTED_TYPES.items():
            if isinstance(merged.get(key), dict):
                merged[key] = cls_type(**merged[key])

        # Alias "inference" -> "inference_params"
        if isinstance(merged.get("inference"), dict):
            merged["inference_params"] = merged.pop("inference")

        # Convert llm_groups dict to LLMGroup instances
        if isinstance(merged.get("llm_groups"), dict):
            merged["llm_groups"] = {
                name: LLMGroup(name=name, **g)
                for name, g in merged["llm_groups"].items()
                if isinstance(g, dict)
            }
        return merged

    @classmethod
    def load(cls) -> Config:
        """Load and merge configuration: tau.json → env vars → defaults."""
        file_cfg = cls._load_file_config()
        merged = cls._apply_env_overrides(file_cfg)
        merged = cls._merge_nested(merged)

        if not merged.get("llm_groups"):
            raise ValueError(
                "No LLM groups configured. "
                "Define at least one group in tau.json under 'llm_groups'."
            )
        if not merged.get("llm_group_name") and merged["llm_groups"]:
            merged["llm_group_name"] = next(iter(merged["llm_groups"]))
        return cls(**merged)


# Module-level config cache — explicit, type-safe, and easy to reason about.
_config_cache: Config | None = None


def get_config() -> Config:
    """Load and return the global configuration.

    Cached after first call — subsequent calls return the same Config instance.
    Call ``reset_config_cache()`` to force a reload.
    """
    global _config_cache
    if _config_cache is None:
        _config_cache = Config.load()
    return _config_cache


def reset_config_cache() -> None:
    """Force ``get_config()`` to reload from disk on next call."""
    global _config_cache
    _config_cache = None
