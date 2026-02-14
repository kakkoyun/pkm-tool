"""Additional tests for aggregator exception handling."""

from datetime import date
from pathlib import Path

import pytest

from pkm_tool.aggregator import aggregate_data


@pytest.fixture
def weekend_config(tmp_path: Path) -> Path:
    """Create a config for testing weekend exclusion."""
    config_path = tmp_path / "weekend_config.yaml"
    config_content = """
github:
  enabled: true
  exclude_weekends: true
  config:
    token: test_token

wakatime:
  enabled: true
  exclude_weekends: true
  config:
    api_key: test_key

atlassian:
  enabled: true
  exclude_weekends: true
  config:
    base_url: https://test.atlassian.net
    username: test@example.com
    api_token: test_token

apple_calendar:
  enabled: true
  exclude_weekends: true

things:
  enabled: true
  exclude_weekends: true

google_docs:
  enabled: true
  exclude_weekends: true
  config:
    access_token: test_token

whoop:
  enabled: true
  exclude_weekends: true
  config:
    access_token: test_token
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def error_config(tmp_path: Path) -> Path:
    """Create a config for testing error handling."""
    config_path = tmp_path / "error_config.yaml"
    config_content = """
github:
  enabled: true
  config:
    token: test_token

wakatime:
  enabled: true
  config:
    api_key: test_key

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
  enabled: true
  config:
    access_token: test_token

whoop:
  enabled: true
  config:
    access_token: test_token
"""
    config_path.write_text(config_content)
    return config_path


class TestAggregatorWeekendExclusion:
    """Tests for weekend exclusion behavior."""

    def test_skip_all_sources_on_weekend(
        self, weekend_config: Path, mock_platform_linux: None, mocker
    ) -> None:
        """Test that all sources are skipped on weekend when configured."""
        # Use a Saturday
        target_date = date(2025, 11, 22)  # Saturday

        # Mock things library to avoid database access
        mocker.patch("things.todos", return_value=[])

        data = aggregate_data(target_date, str(weekend_config))

        # All sources should be empty because it's weekend and exclude_weekends is True
        assert data.github_activities == []
        assert data.wakatime_activities == []
        assert data.atlassian_items == []
        assert data.calendar_events == []
        assert data.things_tasks == []
        assert data.google_docs == []
        assert data.whoop_recovery is None
        assert data.whoop_sleep == []
        assert data.whoop_workouts == []

    def test_weekday_data_fetched_normally(
        self, weekend_config: Path, mock_github_client, mock_github_auth, mocker
    ) -> None:
        """Test that data is fetched normally on weekdays."""
        # Use a Friday (weekday) that matches mock data date
        target_date = date(2025, 11, 21)  # Friday

        # Mock things library to avoid database access
        mocker.patch("things.todos", return_value=[])

        data = aggregate_data(target_date, str(weekend_config))

        # GitHub should have data on weekday
        assert len(data.github_activities) > 0


class TestAggregatorExceptionHandling:
    """Tests for aggregator exception handling."""

    def test_apple_calendar_exception(self, error_config: Path, mocker) -> None:
        """Test that apple_calendar exceptions are caught and stored in metadata."""
        target_date = date(2025, 11, 21)

        # Mock apple_calendar to raise exception
        mocker.patch(
            "pkm_tool.aggregator.fetch_calendar_events",
            side_effect=Exception("Calendar fetch failed"),
        )
        # Mock things library to avoid database access
        mocker.patch("things.todos", return_value=[])
        # Mock other sources to return empty lists
        mocker.patch("pkm_tool.aggregator.fetch_github_activities", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_wakatime_activities", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_atlassian_items", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_google_docs", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_recovery", return_value=None)
        mocker.patch("pkm_tool.aggregator.fetch_whoop_sleep", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_workouts", return_value=[])

        data = aggregate_data(target_date, str(error_config))

        assert "apple_calendar_error" in data.metadata
        assert "Calendar fetch failed" in data.metadata["apple_calendar_error"]

    def test_github_exception(self, error_config: Path, mocker) -> None:
        """Test that github exceptions are caught and stored in metadata."""
        target_date = date(2025, 11, 21)

        # Mock github to raise exception
        mocker.patch(
            "pkm_tool.aggregator.fetch_github_activities",
            side_effect=Exception("GitHub API failed"),
        )
        # Mock things library to avoid database access
        mocker.patch("things.todos", return_value=[])
        # Mock other sources to return empty lists
        mocker.patch("pkm_tool.aggregator.fetch_calendar_events", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_wakatime_activities", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_atlassian_items", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_google_docs", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_recovery", return_value=None)
        mocker.patch("pkm_tool.aggregator.fetch_whoop_sleep", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_workouts", return_value=[])

        data = aggregate_data(target_date, str(error_config))

        assert "github_error" in data.metadata
        assert "GitHub API failed" in data.metadata["github_error"]

    def test_atlassian_exception(self, error_config: Path, mocker) -> None:
        """Test that atlassian exceptions are caught and stored in metadata."""
        target_date = date(2025, 11, 21)

        # Mock atlassian to raise exception
        mocker.patch(
            "pkm_tool.aggregator.fetch_atlassian_items",
            side_effect=Exception("Atlassian API failed"),
        )
        # Mock things library to avoid database access
        mocker.patch("things.todos", return_value=[])
        # Mock other sources to return empty lists
        mocker.patch("pkm_tool.aggregator.fetch_calendar_events", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_github_activities", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_wakatime_activities", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_google_docs", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_recovery", return_value=None)
        mocker.patch("pkm_tool.aggregator.fetch_whoop_sleep", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_workouts", return_value=[])

        data = aggregate_data(target_date, str(error_config))

        assert "atlassian_error" in data.metadata
        assert "Atlassian API failed" in data.metadata["atlassian_error"]

    def test_things_exception(self, error_config: Path, mocker) -> None:
        """Test that things exceptions are caught and stored in metadata."""
        target_date = date(2025, 11, 21)

        # Mock things to raise exception
        mocker.patch(
            "pkm_tool.aggregator.fetch_things_tasks",
            side_effect=Exception("Things database failed"),
        )
        # Mock other sources to return empty lists
        mocker.patch("pkm_tool.aggregator.fetch_calendar_events", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_github_activities", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_wakatime_activities", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_atlassian_items", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_google_docs", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_recovery", return_value=None)
        mocker.patch("pkm_tool.aggregator.fetch_whoop_sleep", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_workouts", return_value=[])

        data = aggregate_data(target_date, str(error_config))

        assert "things_error" in data.metadata
        assert "Things database failed" in data.metadata["things_error"]

    def test_wakatime_exception(self, error_config: Path, mocker) -> None:
        """Test that wakatime exceptions are caught and stored in metadata."""
        target_date = date(2025, 11, 21)

        # Mock wakatime to raise exception
        mocker.patch(
            "pkm_tool.aggregator.fetch_wakatime_activities",
            side_effect=Exception("Wakatime API failed"),
        )
        # Mock things library to avoid database access
        mocker.patch("things.todos", return_value=[])
        # Mock other sources to return empty lists
        mocker.patch("pkm_tool.aggregator.fetch_calendar_events", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_github_activities", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_atlassian_items", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_google_docs", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_recovery", return_value=None)
        mocker.patch("pkm_tool.aggregator.fetch_whoop_sleep", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_workouts", return_value=[])

        data = aggregate_data(target_date, str(error_config))

        assert "wakatime_error" in data.metadata
        assert "Wakatime API failed" in data.metadata["wakatime_error"]

    def test_google_docs_exception(self, error_config: Path, mocker) -> None:
        """Test that google_docs exceptions are caught and stored in metadata."""
        target_date = date(2025, 11, 21)

        # Mock google_docs to raise exception
        mocker.patch(
            "pkm_tool.aggregator.fetch_google_docs",
            side_effect=Exception("Google API failed"),
        )
        # Mock things library to avoid database access
        mocker.patch("things.todos", return_value=[])
        # Mock other sources to return empty lists
        mocker.patch("pkm_tool.aggregator.fetch_calendar_events", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_github_activities", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_wakatime_activities", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_atlassian_items", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_recovery", return_value=None)
        mocker.patch("pkm_tool.aggregator.fetch_whoop_sleep", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_workouts", return_value=[])

        data = aggregate_data(target_date, str(error_config))

        assert "google_docs_error" in data.metadata
        assert "Google API failed" in data.metadata["google_docs_error"]

    def test_whoop_exception(self, error_config: Path, mocker) -> None:
        """Test that whoop exceptions are caught and stored in metadata."""
        target_date = date(2025, 11, 21)

        # Mock whoop recovery to raise exception
        mocker.patch(
            "pkm_tool.aggregator.fetch_whoop_recovery",
            side_effect=Exception("Whoop API failed"),
        )
        # Mock things library to avoid database access
        mocker.patch("things.todos", return_value=[])
        # Mock other sources to return empty lists
        mocker.patch("pkm_tool.aggregator.fetch_calendar_events", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_github_activities", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_wakatime_activities", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_atlassian_items", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_google_docs", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_sleep", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_workouts", return_value=[])

        data = aggregate_data(target_date, str(error_config))

        # Each Whoop endpoint gets its own error key after normalization
        assert "whoop_recovery_error" in data.metadata
        assert "Whoop API failed" in data.metadata["whoop_recovery_error"]

    def test_multiple_exceptions(self, error_config: Path, mocker) -> None:
        """Test that multiple source exceptions are all captured."""
        target_date = date(2025, 11, 21)

        # Mock multiple sources to raise exceptions
        mocker.patch(
            "pkm_tool.aggregator.fetch_github_activities",
            side_effect=Exception("GitHub failed"),
        )
        mocker.patch(
            "pkm_tool.aggregator.fetch_wakatime_activities",
            side_effect=Exception("Wakatime failed"),
        )
        # Mock things library to avoid database access
        mocker.patch("things.todos", return_value=[])
        # Mock other sources to return empty lists
        mocker.patch("pkm_tool.aggregator.fetch_calendar_events", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_atlassian_items", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_google_docs", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_recovery", return_value=None)
        mocker.patch("pkm_tool.aggregator.fetch_whoop_sleep", return_value=[])
        mocker.patch("pkm_tool.aggregator.fetch_whoop_workouts", return_value=[])

        data = aggregate_data(target_date, str(error_config))

        assert "github_error" in data.metadata
        assert "wakatime_error" in data.metadata
        assert "GitHub failed" in data.metadata["github_error"]
        assert "Wakatime failed" in data.metadata["wakatime_error"]


class TestAggregatorCacheConfig:
    """Tests for aggregator cache configuration."""

    def test_aggregation_with_cache_enabled(self, tmp_path: Path, mocker) -> None:
        """Test aggregation when cache is enabled."""
        config_path = tmp_path / "cache_config.yaml"
        config_content = f"""
cache:
  enabled: true
  directory: {tmp_path / "cache"}
  ttl_hours: 24

github:
  enabled: false

wakatime:
  enabled: true
  config:
    api_key: test_key

atlassian:
  enabled: false

apple_calendar:
  enabled: false

things:
  enabled: false

google_docs:
  enabled: false

whoop:
  enabled: false
"""
        config_path.write_text(config_content)

        target_date = date(2025, 11, 21)

        # Mock wakatime to verify it receives cache config
        mock_fetch = mocker.patch(
            "pkm_tool.aggregator.fetch_wakatime_activities",
            return_value=[],
        )

        data = aggregate_data(target_date, str(config_path))
        _ = data  # Used to ensure no exceptions occurred

        # Verify cache config was passed
        assert mock_fetch.called
        args, kwargs = mock_fetch.call_args
        # Third argument should be cache_config
        assert len(args) == 3 or "cache_config" in kwargs
