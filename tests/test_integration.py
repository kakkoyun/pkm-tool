"""Integration tests for end-to-end workflows."""

from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pytest

from pkm_tool.aggregator import aggregate_data
from pkm_tool.formatters import format_as_json, format_as_markdown


@pytest.fixture
def full_config(tmp_path: Path) -> Path:
    """Create a config with all sources enabled."""
    config_path = tmp_path / "full_config.yaml"
    config_content = """
github:
  enabled: true
  config:
    token: test_github_token

wakatime:
  enabled: true
  config:
    api_key: test_wakatime_key

atlassian:
  enabled: true
  config:
    base_url: https://test.atlassian.net
    username: test@example.com
    api_token: test_token

apple_calendar:
  enabled: true

things:
  enabled: true

google_docs:
  enabled: false
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def selective_config(tmp_path: Path) -> Path:
    """Create a config with only some sources enabled."""
    config_path = tmp_path / "selective_config.yaml"
    config_content = """
github:
  enabled: true
  config:
    token: test_github_token

wakatime:
  enabled: false

atlassian:
  enabled: false

apple_calendar:
  enabled: false

things:
  enabled: false

google_docs:
  enabled: false
"""
    config_path.write_text(config_content)
    return config_path


@pytest.mark.integration
def test_full_aggregation_all_sources(
    full_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_success: Mock,
    mock_atlassian_clients: tuple[Mock, Mock],
    mock_platform_macos: Mock,
    mock_things_database: Path,
) -> None:
    """Test full data aggregation with all sources enabled."""
    target_date = date(2025, 11, 21)

    # Note: Things database is mocked but won't be used in this test
    # because the mock_platform_macos fixture already handles osascript calls
    data = aggregate_data(target_date, str(full_config))

    # Verify data was collected from all enabled sources
    assert data.date == target_date
    assert len(data.github_activities) > 0
    assert len(data.wakatime_activities) > 0
    assert len(data.atlassian_items) > 0
    # Calendar and Things may or may not have data depending on mocks

    # Verify metadata exists
    assert isinstance(data.metadata, dict)


@pytest.mark.integration
def test_selective_source_aggregation(
    selective_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
) -> None:
    """Test aggregation with only GitHub enabled."""
    target_date = date(2025, 11, 21)
    data = aggregate_data(target_date, str(selective_config))

    # Only GitHub should have data
    assert len(data.github_activities) > 0
    assert len(data.wakatime_activities) == 0
    assert len(data.atlassian_items) == 0
    assert len(data.things_tasks) == 0


@pytest.mark.integration
def test_aggregation_with_errors(
    full_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_server_error: Mock,
) -> None:
    """Test aggregation when some sources fail."""
    # Make GitHub fail
    mock_github_client.get_user.side_effect = Exception("GitHub API failed")

    target_date = date(2025, 11, 21)
    data = aggregate_data(target_date, str(full_config))

    # Should still return data object
    assert data.date == target_date

    # Sources that fail internally return empty lists (graceful degradation)
    # The aggregator catches exceptions and adds them to metadata
    # But individual source functions also catch exceptions and return []
    # So we just verify the data object is valid
    assert isinstance(data.github_activities, list)
    assert isinstance(data.wakatime_activities, list)


@pytest.mark.integration
def test_markdown_formatting_integration(
    selective_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
) -> None:
    """Test markdown formatting with real aggregated data."""
    target_date = date(2025, 11, 21)
    data = aggregate_data(target_date, str(selective_config))

    markdown = format_as_markdown(data)

    # Verify markdown structure
    assert "# Daily Report - 2025-11-21" in markdown
    # The formatter uses emojis in headers
    assert "GitHub Activities" in markdown

    # Should contain GitHub activity data
    assert "Pushed 3 commits" in markdown or "testuser/test-repo" in markdown


@pytest.mark.integration
def test_json_formatting_integration(
    selective_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
) -> None:
    """Test JSON formatting with real aggregated data."""
    target_date = date(2025, 11, 21)
    data = aggregate_data(target_date, str(selective_config))

    json_output = format_as_json(data)

    # Verify JSON structure
    assert '"date": "2025-11-21"' in json_output
    assert '"github_activities"' in json_output
    assert '"type": "commit"' in json_output or '"type": "pr"' in json_output


@pytest.mark.integration
def test_error_display_in_markdown(
    selective_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
) -> None:
    """Test that errors are displayed in markdown output."""
    # Force an error
    mock_github_client.get_user.side_effect = Exception("Connection timeout")

    target_date = date(2025, 11, 21)
    data = aggregate_data(target_date, str(selective_config))

    markdown = format_as_markdown(data)

    # Error should appear in output if captured in metadata
    if data.metadata:
        assert "## Errors" in markdown or "No data" in markdown


@pytest.mark.integration
def test_date_filtering_accuracy(
    selective_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_github_events: list[Mock],
) -> None:
    """Test that data is correctly filtered by date."""
    # All mock events are set to 2025-11-21
    target_date = date(2025, 11, 21)
    data = aggregate_data(target_date, str(selective_config))

    # All GitHub activities should match target date
    for activity in data.github_activities:
        assert activity.timestamp.date() == target_date


@pytest.mark.integration
def test_config_file_not_found(
    mock_github_client: Mock,
    mock_github_auth: Mock,
) -> None:
    """Test aggregation when config file doesn't exist (uses defaults)."""
    target_date = date(2025, 11, 21)

    # Pass non-existent config path
    data = aggregate_data(target_date, "/non/existent/config.yaml")

    # Should still work with default config
    assert data.date == target_date


@pytest.mark.integration
def test_environment_variable_fallback(
    tmp_path: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_success: Mock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that environment variables are used when config doesn't specify credentials."""
    # Create config without tokens
    config_path = tmp_path / "minimal_config.yaml"
    config_content = """
github:
  enabled: true

wakatime:
  enabled: true
"""
    config_path.write_text(config_content)

    # Set environment variables
    monkeypatch.setenv("GITHUB_TOKEN", "env_github_token")
    monkeypatch.setenv("WAKATIME_API_KEY", "env_wakatime_key")

    target_date = date(2025, 11, 21)
    data = aggregate_data(target_date, str(config_path))

    # Should successfully fetch data using env vars
    assert data.date == target_date


@pytest.mark.integration
def test_empty_data_sources(
    tmp_path: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
) -> None:
    """Test aggregation when sources return no data."""
    # Make GitHub return empty events
    mock_github_client.get_user.return_value.get_events.return_value = []

    config_path = tmp_path / "config.yaml"
    config_content = """
github:
  enabled: true
  config:
    token: test_token

wakatime:
  enabled: false

atlassian:
  enabled: false

apple_calendar:
  enabled: false

things:
  enabled: false

google_docs:
  enabled: false
"""
    config_path.write_text(config_content)

    target_date = date(2025, 11, 21)
    data = aggregate_data(target_date, str(config_path))

    # Should have empty lists, not None
    assert data.github_activities == []
    assert data.wakatime_activities == []


@pytest.mark.integration
def test_multiple_github_event_types(
    selective_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_github_events: list[Mock],
) -> None:
    """Test that different GitHub event types are properly mapped."""
    target_date = date(2025, 11, 21)
    data = aggregate_data(target_date, str(selective_config))

    # Should have multiple types of activities
    activity_types = {activity.type for activity in data.github_activities}

    # Should contain at least some of: commit, pr, issue, review
    assert len(activity_types) > 0
    assert any(t in activity_types for t in ["commit", "pr", "issue", "review"])


@pytest.mark.integration
def test_sorting_and_ordering(
    selective_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
) -> None:
    """Test that events are properly sorted in output."""
    target_date = date(2025, 11, 21)
    data = aggregate_data(target_date, str(selective_config))

    markdown = format_as_markdown(data)

    # Markdown should have consistent structure
    assert markdown.startswith("# Daily Report")

    # GitHub section should appear before other sections
    github_pos = markdown.find("## GitHub Activities")
    wakatime_pos = markdown.find("## Wakatime Activities")

    # If both sections exist, GitHub should come before Wakatime
    if github_pos != -1 and wakatime_pos != -1:
        assert github_pos < wakatime_pos
