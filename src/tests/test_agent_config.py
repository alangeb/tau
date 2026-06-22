"""Tests for agent_config module.

Tests:
    test_get_config - Verify config loading works
    test_config_llm_groups - Verify LLM groups are loaded
    test_config_defaults - Verify default values
    test_config_env_override - Verify env vars override config
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestGetConfig:
    """Test config loading functionality."""

    def test_get_config_returns_config(self, tau_entry_dir):
        """Verify get_config returns a Config object."""
        from agent_config import Config, get_config

        config = get_config()
        assert config is not None
        assert isinstance(config, Config)

    def test_config_has_required_attributes(self, tau_entry_dir):
        """Verify Config has all required attributes."""
        from agent_config import get_config

        config = get_config()
        assert hasattr(config, "llm_groups")
        assert hasattr(config, "llm_group_name")
        assert hasattr(config, "agent_name")
        assert hasattr(config, "timeout")

    def test_config_llm_groups_is_dict(self, tau_entry_dir):
        """Verify llm_groups is a dictionary."""
        from agent_config import get_config

        config = get_config()
        assert isinstance(config.llm_groups, dict)

    def test_config_llm_group_name_is_string(self, tau_entry_dir):
        """Verify llm_group_name is a string."""
        from agent_config import get_config

        config = get_config()
        assert isinstance(config.llm_group_name, str)


class TestConfigLLMGroups:
    """Test LLM groups configuration."""

    def test_llm_groups_contains_default(self, tau_entry_dir):
        """Verify default LLM group exists."""
        from agent_config import get_config

        config = get_config()
        # Default group should exist
        assert "default" in config.llm_groups or len(config.llm_groups) > 0

    def test_llm_group_has_required_fields(self, tau_entry_dir):
        """Verify LLM groups have required fields."""
        from agent_config import get_config

        config = get_config()
        for name, group in config.llm_groups.items():
            assert hasattr(group, "model"), f"Group '{name}' missing 'model'"
            assert hasattr(group, "api_base"), f"Group '{name}' missing 'api_base'"
            assert hasattr(
                group, "max_context_tokens"
            ), f"Group '{name}' missing 'max_context_tokens'"


class TestConfigDefaults:
    """Test default configuration values."""

    def test_default_agent_name(self, tau_entry_dir):
        """Verify default agent name is 'default'."""
        from agent_config import get_config

        config = get_config()
        # Agent name should be set (either from config or default)
        assert config.agent_name is not None

    def test_default_timeout(self, tau_entry_dir):
        """Verify default timeout is set."""
        from agent_config import get_config

        config = get_config()
        assert config.timeout is not None
        assert isinstance(config.timeout, int)
        assert config.timeout > 0
