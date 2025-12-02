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


def test_section_config_defaults() -> None:
    """Test SectionConfig defaults."""
    from pkm_tool.config import DEFAULT_SECTION_ORDER, DEFAULT_SECTION_TITLES, SectionConfig

    config = SectionConfig()
    assert config.titles == DEFAULT_SECTION_TITLES
    assert config.order == DEFAULT_SECTION_ORDER


def test_config_sections_defaults() -> None:
    """Test Config.sections uses defaults."""
    config = Config()
    assert config.sections is not None
    assert "calendar_events" in config.sections.titles
    assert "github_activities" in config.sections.order


def test_load_config_with_custom_sections() -> None:
    """Test loading config with custom section titles and order."""
    yaml_content = """
sections:
  titles:
    calendar_events: "📆 My Schedule"
    github_activities: "Code Changes"
  order:
    - github_activities
    - calendar_events
    - things_tasks

github:
  enabled: true
"""

    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        try:
            config = load_config(f.name)
            assert config.sections.titles["calendar_events"] == "📆 My Schedule"
            assert config.sections.titles["github_activities"] == "Code Changes"
            assert config.sections.order[0] == "github_activities"
            assert config.sections.order[1] == "calendar_events"
        finally:
            Path(f.name).unlink()


def test_load_config_with_partial_section_titles() -> None:
    """Test loading config with only some section titles customized."""
    yaml_content = """
sections:
  titles:
    calendar_events: "Schedule"
  # Keep default order

github:
  enabled: true
"""

    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        try:
            config = load_config(f.name)
            assert config.sections.titles["calendar_events"] == "Schedule"
            # When titles dict is provided in YAML, it completely replaces the default
            # Only the specified keys will be present (YAML behavior)
            assert "github_activities" not in config.sections.titles
        finally:
            Path(f.name).unlink()
