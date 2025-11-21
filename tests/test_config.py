"""Tests for configuration."""

from pathlib import Path
from tempfile import NamedTemporaryFile

from pkm_tool.config import Config, SourceConfig, load_config


def test_source_config_defaults() -> None:
    """Test SourceConfig defaults."""
    config = SourceConfig()
    assert config.enabled is True
    assert config.config == {}


def test_config_defaults() -> None:
    """Test Config defaults."""
    config = Config()
    assert config.apple_calendar.enabled is True
    assert config.github.enabled is True
    assert config.atlassian.enabled is True


def test_load_config_no_file() -> None:
    """Test loading config with no file."""
    config = load_config()
    assert isinstance(config, Config)
    assert config.github.enabled is True


def test_load_config_from_file() -> None:
    """Test loading config from YAML file."""
    yaml_content = """
github:
  enabled: false
  config:
    token: test_token

wakatime:
  enabled: true
  config:
    api_key: test_key
"""

    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        try:
            config = load_config(f.name)
            assert config.github.enabled is False
            assert config.github.config.get("token") == "test_token"
            assert config.wakatime.enabled is True
            assert config.wakatime.config.get("api_key") == "test_key"
        finally:
            Path(f.name).unlink()
