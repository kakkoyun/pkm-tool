"""Tests for MCP server functionality."""

from datetime import date, datetime
from unittest.mock import Mock, patch

import pytest

from pkm_tool.models import AggregatedData, GitHubActivity, WakatimeActivity


@pytest.fixture
def mock_aggregated_data() -> AggregatedData:
    """Create mock aggregated data."""
    target_date = date(2025, 12, 1)
    data = AggregatedData(date=target_date)
    data.github_activities = [
        GitHubActivity(
            type="PushEvent",
            repository="test/repo",
            title="Pushed 2 commits",
            url="https://github.com/test/repo",
            timestamp=datetime(2025, 12, 1, 10, 0, 0),
        )
    ]
    data.wakatime_activities = [
        WakatimeActivity(
            project="test-project",
            duration_seconds=3600,
            language="Python",
        )
    ]
    return data


@pytest.fixture
def mock_config() -> Mock:
    """Create mock config."""
    config = Mock()
    config.apple_calendar = Mock(config={})
    config.github = Mock(config={})
    config.atlassian = Mock(config={})
    config.things = Mock(config={})
    config.wakatime = Mock(config={})
    config.google_docs = Mock(config={})
    config.whoop = Mock(config={})
    return config


@pytest.mark.unit
def test_create_mcp_server() -> None:
    """Test MCP server creation."""
    from pkm_tool.mcp_server import create_mcp_server

    server = create_mcp_server()
    assert server is not None
    assert server.name == "pkm-tool"


@pytest.mark.unit
def test_parse_date_string() -> None:
    """Test date string parsing."""
    from pkm_tool.mcp_server.server import _parse_date_string

    # Test explicit date
    result = _parse_date_string("2025-12-01")
    assert result == date(2025, 12, 1)

    # Test None (should return today)
    result = _parse_date_string(None)
    assert isinstance(result, date)

    # Test invalid date
    with pytest.raises(ValueError):
        _parse_date_string("not-a-date-12345")


@pytest.mark.unit
def test_fetch_aggregated_data(mock_aggregated_data: AggregatedData) -> None:
    """Test fetching aggregated data."""
    from pkm_tool.mcp_server.server import _fetch_aggregated_data

    target_date = date(2025, 12, 1)

    with patch("pkm_tool.mcp_server.server.aggregate_data", return_value=mock_aggregated_data):
        result = _fetch_aggregated_data(target_date)

    assert result is not None
    assert result.date == target_date
    assert len(result.github_activities) == 1
    assert len(result.wakatime_activities) == 1


@pytest.mark.unit
def test_fetch_aggregated_data_with_config_path(mock_aggregated_data: AggregatedData) -> None:
    """Test fetching aggregated data with config path."""
    from pkm_tool.mcp_server.server import _fetch_aggregated_data

    target_date = date(2025, 12, 1)

    with patch("pkm_tool.mcp_server.server.aggregate_data", return_value=mock_aggregated_data):
        result = _fetch_aggregated_data(target_date, config_path="/path/to/config.yaml")

    assert result is not None
    assert result.date == target_date


@pytest.mark.unit
def test_fetch_source_data_github(mock_aggregated_data: AggregatedData, mock_config: Mock) -> None:
    """Test fetching data from GitHub source."""
    from pkm_tool.mcp_server.server import _fetch_source_data

    target_date = date(2025, 12, 1)

    with patch(
        "pkm_tool.mcp_server.server.fetch_github_activities",
        return_value=mock_aggregated_data.github_activities,
    ):
        with patch("pkm_tool.mcp_server.server.load_config", return_value=mock_config):
            result = _fetch_source_data("github", target_date)

    assert result is not None
    assert result.date == target_date
    assert len(result.github_activities) == 1


@pytest.mark.unit
def test_fetch_source_data_calendar(mock_config: Mock) -> None:
    """Test fetching data from calendar source."""
    from pkm_tool.mcp_server.server import _fetch_source_data

    target_date = date(2025, 12, 1)

    with patch("pkm_tool.mcp_server.server.fetch_calendar_events", return_value=[]):
        with patch("pkm_tool.mcp_server.server.load_config", return_value=mock_config):
            result = _fetch_source_data("calendar", target_date)

    assert result is not None
    assert result.date == target_date
    assert len(result.calendar_events) == 0


@pytest.mark.unit
def test_fetch_source_data_atlassian(mock_config: Mock) -> None:
    """Test fetching data from Atlassian source."""
    from pkm_tool.mcp_server.server import _fetch_source_data

    target_date = date(2025, 12, 1)

    with patch("pkm_tool.mcp_server.server.fetch_atlassian_items", return_value=[]):
        with patch("pkm_tool.mcp_server.server.load_config", return_value=mock_config):
            result = _fetch_source_data("atlassian", target_date)

    assert result is not None
    assert result.date == target_date
    assert len(result.atlassian_items) == 0


@pytest.mark.unit
def test_fetch_source_data_things(mock_config: Mock) -> None:
    """Test fetching data from Things source."""
    from pkm_tool.mcp_server.server import _fetch_source_data

    target_date = date(2025, 12, 1)

    with patch("pkm_tool.mcp_server.server.fetch_things_tasks", return_value=[]):
        with patch("pkm_tool.mcp_server.server.load_config", return_value=mock_config):
            result = _fetch_source_data("things", target_date)

    assert result is not None
    assert result.date == target_date
    assert len(result.things_tasks) == 0


@pytest.mark.unit
def test_fetch_source_data_wakatime(mock_config: Mock) -> None:
    """Test fetching data from Wakatime source."""
    from pkm_tool.mcp_server.server import _fetch_source_data

    target_date = date(2025, 12, 1)

    with patch("pkm_tool.mcp_server.server.fetch_wakatime_activities", return_value=[]):
        with patch("pkm_tool.mcp_server.server.load_config", return_value=mock_config):
            result = _fetch_source_data("wakatime", target_date)

    assert result is not None
    assert result.date == target_date
    assert len(result.wakatime_activities) == 0


@pytest.mark.unit
def test_fetch_source_data_google_docs(mock_config: Mock) -> None:
    """Test fetching data from Google Docs source."""
    from pkm_tool.mcp_server.server import _fetch_source_data

    target_date = date(2025, 12, 1)

    with patch("pkm_tool.mcp_server.server.fetch_google_docs", return_value=[]):
        with patch("pkm_tool.mcp_server.server.load_config", return_value=mock_config):
            result = _fetch_source_data("google-docs", target_date)

    assert result is not None
    assert result.date == target_date
    assert len(result.google_docs) == 0


@pytest.mark.unit
def test_fetch_source_data_invalid_source(mock_config: Mock) -> None:
    """Test fetching data from invalid source."""
    from pkm_tool.mcp_server.server import _fetch_source_data

    target_date = date(2025, 12, 1)

    with patch("pkm_tool.mcp_server.server.load_config", return_value=mock_config):
        with pytest.raises(ValueError, match="Unknown source"):
            _fetch_source_data("invalid_source", target_date)


@pytest.mark.unit
def test_fetch_source_data_whoop(mock_config: Mock) -> None:
    """Test fetching data from Whoop source."""
    from pkm_tool.mcp_server.server import _fetch_source_data

    target_date = date(2025, 12, 1)

    with patch("pkm_tool.mcp_server.server.fetch_whoop_recovery", return_value=None):
        with patch("pkm_tool.mcp_server.server.fetch_whoop_sleep", return_value=[]):
            with patch("pkm_tool.mcp_server.server.fetch_whoop_workouts", return_value=[]):
                with patch("pkm_tool.mcp_server.server.load_config", return_value=mock_config):
                    result = _fetch_source_data("whoop", target_date)

    assert result is not None
    assert result.date == target_date
    assert result.whoop_recovery is None
    assert len(result.whoop_sleep) == 0
    assert len(result.whoop_workouts) == 0


@pytest.mark.unit
def test_fetch_source_data_with_config_path(mock_config: Mock) -> None:
    """Test fetching source data with config path."""
    from pkm_tool.mcp_server.server import _fetch_source_data

    target_date = date(2025, 12, 1)

    with patch("pkm_tool.mcp_server.server.fetch_github_activities", return_value=[]):
        with patch("pkm_tool.mcp_server.server.load_config", return_value=mock_config):
            result = _fetch_source_data("github", target_date, config_path="/path/to/config.yaml")

    assert result is not None
    assert result.date == target_date
