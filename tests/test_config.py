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
    assert config.apple_calendar.enabled is True
    assert config.github.enabled is True
    assert config.atlassian.enabled is True
    assert config.output_filename_template == "{date} ({day_abbr}).{format}"
    assert config.output_directory == "."


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


def test_config_output_settings() -> None:
    """Test output settings in config."""
    yaml_content = """
output_filename_template: "{year}-{month}-{day}.{format}"
output_directory: "./daily-notes"

github:
  enabled: true
"""

    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        try:
            config = load_config(f.name)
            assert config.output_filename_template == "{year}-{month}-{day}.{format}"
            assert config.output_directory == "./daily-notes"
        finally:
            Path(f.name).unlink()


def test_config_exclude_weekends() -> None:
    """Test exclude_weekends in source config."""
    yaml_content = """
github:
  enabled: true
  exclude_weekends: true
  config:
    use_gh_cli: true

wakatime:
  enabled: true
  exclude_weekends: false
"""

    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        try:
            config = load_config(f.name)
            assert config.github.exclude_weekends is True
            assert config.wakatime.exclude_weekends is False
        finally:
            Path(f.name).unlink()


def test_source_config_title_and_order() -> None:
    """Test SourceConfig title and order fields."""
    from pkm_tool.config import SourceConfig

    # Default values
    config = SourceConfig()
    assert config.title is None
    assert config.order is None

    # Custom values
    config = SourceConfig(title="Custom Title", order=5)
    assert config.title == "Custom Title"
    assert config.order == 5


def test_config_get_source_title_default() -> None:
    """Test Config.get_source_title uses defaults when not set."""
    config = Config()
    assert config.get_source_title("github") == "🐙 GitHub Activities"
    assert config.get_source_title("apple_calendar") == "📅 Calendar Events"


def test_config_get_source_title_custom() -> None:
    """Test Config.get_source_title uses custom title when set."""
    from pkm_tool.config import SourceConfig

    config = Config(
        github=SourceConfig(title="Code Changes"),
    )
    assert config.get_source_title("github") == "Code Changes"
    # Other sources still use defaults
    assert config.get_source_title("apple_calendar") == "📅 Calendar Events"


def test_config_get_ordered_sources_default() -> None:
    """Test Config.get_ordered_sources returns config definition order by default."""
    config = Config()
    sources = config.get_ordered_sources()
    # Should be in config definition order
    assert sources[0] == "apple_calendar"
    assert sources[1] == "github"
    assert sources[2] == "atlassian"


def test_config_get_ordered_sources_custom() -> None:
    """Test Config.get_ordered_sources respects custom order."""
    from pkm_tool.config import SourceConfig

    config = Config(
        github=SourceConfig(order=1),
        apple_calendar=SourceConfig(order=2),
        wakatime=SourceConfig(order=3),
    )
    sources = config.get_ordered_sources()
    # Sources with explicit order come first
    assert sources[0] == "github"
    assert sources[1] == "apple_calendar"
    assert sources[2] == "wakatime"
    # Sources without explicit order follow in config definition order


def test_load_config_with_custom_source_titles() -> None:
    """Test loading config with custom source titles."""
    yaml_content = """
github:
  enabled: true
  title: "Code Changes"

apple_calendar:
  enabled: true
  title: "📆 My Schedule"
"""

    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        try:
            config = load_config(f.name)
            assert config.get_source_title("github") == "Code Changes"
            assert config.get_source_title("apple_calendar") == "📆 My Schedule"
            # Other sources still use defaults
            assert config.get_source_title("wakatime") == "⏱️ Wakatime - Coding Activity"
        finally:
            Path(f.name).unlink()


def test_load_config_with_custom_order() -> None:
    """Test loading config with custom source order."""
    yaml_content = """
github:
  enabled: true
  order: 1

apple_calendar:
  enabled: true
  order: 2

wakatime:
  enabled: true
  order: 3
"""

    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        try:
            config = load_config(f.name)
            sources = config.get_ordered_sources()
            assert sources[0] == "github"
            assert sources[1] == "apple_calendar"
            assert sources[2] == "wakatime"
        finally:
            Path(f.name).unlink()
