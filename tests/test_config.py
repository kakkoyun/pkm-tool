"""Tests for configuration."""

from pathlib import Path
from tempfile import NamedTemporaryFile

from pkm_tool.config import Config, SourceConfig, load_config


def test_source_config_defaults() -> None:
    """Test SourceConfig defaults."""
    config = SourceConfig()
    assert config.enabled is True
    assert config.exclude_weekends is False
    assert config.config == {}


def test_config_defaults() -> None:
    """Test Config defaults."""
    config = Config()
    assert config.exclude_weekends is False
    assert config.apple_calendar.enabled is True
    assert config.apple_calendar.exclude_weekends is False
    assert config.github.enabled is True
    assert config.atlassian.enabled is True
    assert config.whoop.enabled is True


def test_load_config_no_file() -> None:
    """Test loading config with no file."""
    config = load_config()
    assert isinstance(config, Config)
    assert config.github.enabled is True


def test_load_config_from_file() -> None:
    """Test loading config from YAML file."""
    yaml_content = """
exclude_weekends: true

github:
  enabled: false
  exclude_weekends: true
  config:
    token: test_token

wakatime:
  enabled: true
  config:
    api_key: test_key

whoop:
  enabled: true
  config:
    access_token: whoop_token
"""

    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        try:
            config = load_config(f.name)
            assert config.github.enabled is False
            assert config.github.config.get("token") == "test_token"
            assert config.exclude_weekends is True
            assert config.github.exclude_weekends is True
            assert config.wakatime.enabled is True
            assert config.wakatime.config.get("api_key") == "test_key"
            assert config.whoop.enabled is True
            assert config.whoop.config.get("access_token") == "whoop_token"
        finally:
            Path(f.name).unlink()
