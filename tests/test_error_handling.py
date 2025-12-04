"""Comprehensive tests for error handling and fault injection across all sources."""

from datetime import date
from unittest.mock import MagicMock

import httpx
from github import GithubException

from pkm_tool.sources.apple_calendar import fetch_calendar_events
from pkm_tool.sources.atlassian import fetch_atlassian_items
from pkm_tool.sources.github import fetch_github_activities
from pkm_tool.sources.google_docs import fetch_google_docs
from pkm_tool.sources.things import fetch_things_tasks
from pkm_tool.sources.wakatime import fetch_wakatime_activities
from pkm_tool.sources.whoop import (
    fetch_whoop_recovery,
    fetch_whoop_sleep,
    fetch_whoop_workouts,
)


class TestGitHubErrorHandling:
    """Test error handling in GitHub source."""

    def test_github_handles_auth_error(self, mocker):
        """Test that GitHub auth errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {"token": "invalid_token"}

        # Mock Auth and Github to raise GithubException
        mock_auth = mocker.patch("pkm_tool.sources.github.Auth")
        mock_github = mocker.patch("pkm_tool.sources.github.Github")
        mock_github.return_value.get_user.side_effect = GithubException(401, "Bad credentials")

        result = fetch_github_activities(target_date, config)

        assert result == []
        assert mock_auth.Token.called

    def test_github_handles_rate_limit_error(self, mocker):
        """Test that GitHub rate limit errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {"token": "valid_token"}

        # Mock Auth and Github to raise rate limit error
        mocker.patch("pkm_tool.sources.github.Auth")
        mock_github = mocker.patch("pkm_tool.sources.github.Github")
        mock_github.return_value.get_user.side_effect = GithubException(
            403, "API rate limit exceeded"
        )

        result = fetch_github_activities(target_date, config)

        assert result == []

    def test_github_handles_network_error(self, mocker):
        """Test that GitHub network errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {"token": "valid_token"}

        # Mock Auth and Github to raise connection error
        mocker.patch("pkm_tool.sources.github.Auth")
        mock_github = mocker.patch("pkm_tool.sources.github.Github")
        mock_github.return_value.get_user.side_effect = ConnectionError("Network unreachable")

        result = fetch_github_activities(target_date, config)

        assert result == []

    def test_github_handles_missing_token(self, mocker):
        """Test that missing token is handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {}

        # Mock get_source_token to return None
        mocker.patch("pkm_tool.sources.github.get_source_token", return_value=None)

        result = fetch_github_activities(target_date, config)

        assert result == []

    def test_github_handles_unexpected_error(self, mocker):
        """Test that unexpected errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {"token": "valid_token"}

        # Mock Auth and Github to raise unexpected error
        mocker.patch("pkm_tool.sources.github.Auth")
        mock_github = mocker.patch("pkm_tool.sources.github.Github")
        mock_github.return_value.get_user.side_effect = RuntimeError("Unexpected error")

        result = fetch_github_activities(target_date, config)

        assert result == []


class TestWakatimeErrorHandling:
    """Test error handling in Wakatime source."""

    def test_wakatime_handles_auth_error(self, respx_mock):
        """Test that Wakatime auth errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {"api_key": "invalid_key"}

        # Mock API to return 401
        respx_mock.get("https://wakatime.com/api/v1/users/current/summaries").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )

        result = fetch_wakatime_activities(target_date, config)

        assert result == []

    def test_wakatime_handles_network_error(self, mocker):
        """Test that Wakatime network errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {"api_key": "valid_key"}

        # Mock httpx client to raise network error
        mock_client = mocker.patch("pkm_tool.sources.wakatime.create_http_client")
        mock_client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError(
            "Connection failed"
        )

        result = fetch_wakatime_activities(target_date, config)

        assert result == []

    def test_wakatime_handles_missing_token(self, mocker):
        """Test that missing token is handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {}

        # Mock get_source_token to return None
        mocker.patch("pkm_tool.sources.wakatime.get_source_token", return_value=None)

        result = fetch_wakatime_activities(target_date, config)

        assert result == []

    def test_wakatime_handles_malformed_response(self, respx_mock):
        """Test that malformed response is handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {"api_key": "valid_key"}

        # Mock API to return malformed JSON
        respx_mock.get("https://wakatime.com/api/v1/users/current/summaries").mock(
            return_value=httpx.Response(200, json={"invalid": "structure"})
        )

        result = fetch_wakatime_activities(target_date, config)

        # Should handle gracefully even with malformed data
        assert isinstance(result, list)


class TestAtlassianErrorHandling:
    """Test error handling in Atlassian source."""

    def test_atlassian_handles_missing_credentials(self):
        """Test that missing credentials are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {}

        result = fetch_atlassian_items(target_date, config)

        assert result == []

    def test_atlassian_handles_jira_api_error(self, mocker):
        """Test that Jira API errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {
            "base_url": "https://test.atlassian.net",
            "username": "test@example.com",
            "api_token": "test_token",
        }

        # Mock Jira to raise exception
        mock_jira = mocker.patch("pkm_tool.sources.atlassian.Jira")
        mock_jira.return_value.jql.side_effect = Exception("API error")

        # Mock Confluence to return empty
        mock_confluence = mocker.patch("pkm_tool.sources.atlassian.Confluence")
        mock_confluence.return_value.cql.return_value = {"results": []}

        result = fetch_atlassian_items(target_date, config)

        # Should handle Jira error at top level and return empty list without attempting Confluence
        assert result == []

    def test_atlassian_handles_confluence_api_error(self, mocker):
        """Test that Confluence API errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {
            "base_url": "https://test.atlassian.net",
            "username": "test@example.com",
            "api_token": "test_token",
        }

        # Mock Jira to return empty
        mock_jira = mocker.patch("pkm_tool.sources.atlassian.Jira")
        mock_jira.return_value.jql.return_value = {"issues": []}

        # Mock Confluence to raise exception
        mock_confluence = mocker.patch("pkm_tool.sources.atlassian.Confluence")
        mock_confluence.return_value.cql.side_effect = Exception("API error")

        result = fetch_atlassian_items(target_date, config)

        assert result == []

    def test_atlassian_handles_network_error(self, mocker):
        """Test that network errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {
            "base_url": "https://test.atlassian.net",
            "username": "test@example.com",
            "api_token": "test_token",
        }

        # Mock Jira to raise connection error
        mock_jira = mocker.patch("pkm_tool.sources.atlassian.Jira")
        mock_jira.side_effect = ConnectionError("Network unreachable")

        result = fetch_atlassian_items(target_date, config)

        assert result == []


class TestAppleCalendarErrorHandling:
    """Test error handling in Apple Calendar source."""

    def test_apple_calendar_handles_non_macos(self, mocker):
        """Test that non-macOS platform is handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {}

        # Mock uname to return Linux
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value.stdout = "Linux\n"

        result = fetch_calendar_events(target_date, config)

        assert result == []

    def test_apple_calendar_handles_applescript_error(self, mocker):
        """Test that AppleScript errors are handled gracefully."""
        import subprocess

        target_date = date(2025, 11, 21)
        config = {}

        # Mock uname to return Darwin
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = [
            MagicMock(stdout="Darwin\n"),  # First call for platform check
            subprocess.CalledProcessError(1, "osascript", stderr="AppleScript error"),
        ]

        result = fetch_calendar_events(target_date, config)

        assert result == []

    def test_apple_calendar_handles_timeout(self, mocker):
        """Test that AppleScript timeout is handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {}

        # Mock uname to return Darwin, then timeout
        import subprocess

        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = [
            MagicMock(stdout="Darwin\n"),  # First call for platform check
            subprocess.TimeoutExpired("osascript", 30),  # Second call times out
        ]

        result = fetch_calendar_events(target_date, config)

        assert result == []


class TestThingsErrorHandling:
    """Test error handling in Things source."""

    def test_things_handles_non_macos(self, mocker):
        """Test that non-macOS platform is handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {}

        # Mock platform.system to return Linux
        mocker.patch("platform.system", return_value="Linux")

        result = fetch_things_tasks(target_date, config)

        assert result == []

    def test_things_handles_database_error(self, mocker):
        """Test that database errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {}

        # Mock platform.system to return Darwin
        mocker.patch("platform.system", return_value="Darwin")

        # Mock things library to raise exception
        mocker.patch("things.todos", side_effect=Exception("Database error"))

        result = fetch_things_tasks(target_date, config)

        assert result == []

    def test_things_handles_import_error(self, mocker):
        """Test that import errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {}

        # Mock platform.system to return Darwin
        mocker.patch("platform.system", return_value="Darwin")

        # Mock the things.todos function to raise ImportError
        # This simulates the things library not being available
        mocker.patch("things.todos", side_effect=ImportError("things not installed"))

        result = fetch_things_tasks(target_date, config)
        assert result == []


class TestGoogleDocsErrorHandling:
    """Test error handling in Google Docs source."""

    def test_google_docs_handles_auth_error(self, respx_mock):
        """Test that Google Docs auth errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {"access_token": "invalid_token"}

        # Mock API to return 401
        respx_mock.get("https://www.googleapis.com/drive/v3/files").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )

        result = fetch_google_docs(target_date, config)

        assert result == []

    def test_google_docs_handles_missing_token(self, mocker):
        """Test that missing token is handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {}

        # Mock get_source_token to return None
        mocker.patch("pkm_tool.sources.google_docs.get_source_token", return_value=None)

        result = fetch_google_docs(target_date, config)

        assert result == []

    def test_google_docs_handles_network_error(self, mocker):
        """Test that network errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {"access_token": "valid_token"}

        # Mock httpx client to raise network error
        mock_client = mocker.patch("pkm_tool.sources.google_docs.create_http_client")
        mock_client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError(
            "Connection failed"
        )

        result = fetch_google_docs(target_date, config)

        assert result == []


class TestWhoopErrorHandling:
    """Test error handling in Whoop source."""

    def test_whoop_recovery_handles_auth_error(self, respx_mock):
        """Test that Whoop recovery auth errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {"access_token": "invalid_token"}

        # Mock API to return 401
        respx_mock.get("https://api.whoop.com/v1/recovery").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )

        result = fetch_whoop_recovery(target_date, config)

        assert result is None

    def test_whoop_sleep_handles_missing_token(self, mocker):
        """Test that missing token is handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {}

        # Mock get_source_token to return None
        mocker.patch("pkm_tool.sources.whoop.get_source_token", return_value=None)

        result = fetch_whoop_sleep(target_date, config)

        assert result == []

    def test_whoop_workouts_handles_network_error(self, mocker):
        """Test that network errors are handled gracefully."""
        target_date = date(2025, 11, 21)
        config = {"access_token": "valid_token"}

        # Mock httpx client to raise network error
        mock_client = mocker.patch("pkm_tool.sources.whoop.create_http_client")
        mock_client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError(
            "Connection failed"
        )

        result = fetch_whoop_workouts(target_date, config)

        assert result == []


class TestErrorIsolation:
    """Test that errors in one source don't affect others."""

    def test_all_sources_can_fail_independently(self, mocker, tmp_path):
        """Test that all sources can fail without affecting aggregation."""
        from pkm_tool.aggregator import aggregate_data

        target_date = date(2025, 11, 21)

        # Create a config with all sources enabled
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
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)

        # Mock all sources to raise exceptions
        mocker.patch(
            "pkm_tool.aggregator.fetch_calendar_events", side_effect=Exception("Calendar failed")
        )
        mocker.patch(
            "pkm_tool.aggregator.fetch_github_activities", side_effect=Exception("GitHub failed")
        )
        mocker.patch(
            "pkm_tool.aggregator.fetch_atlassian_items", side_effect=Exception("Atlassian failed")
        )
        mocker.patch(
            "pkm_tool.aggregator.fetch_things_tasks", side_effect=Exception("Things failed")
        )
        mocker.patch(
            "pkm_tool.aggregator.fetch_wakatime_activities",
            side_effect=Exception("Wakatime failed"),
        )
        mocker.patch(
            "pkm_tool.aggregator.fetch_google_docs", side_effect=Exception("Google Docs failed")
        )
        mocker.patch(
            "pkm_tool.aggregator.fetch_whoop_recovery",
            side_effect=Exception("Whoop recovery failed"),
        )
        mocker.patch(
            "pkm_tool.aggregator.fetch_whoop_sleep", side_effect=Exception("Whoop sleep failed")
        )
        mocker.patch(
            "pkm_tool.aggregator.fetch_whoop_workouts",
            side_effect=Exception("Whoop workouts failed"),
        )

        # Should not raise - all errors should be caught
        data = aggregate_data(target_date, str(config_path))

        # All data should be empty
        assert data.calendar_events == []
        assert data.github_activities == []
        assert data.atlassian_items == []
        assert data.things_tasks == []
        assert data.wakatime_activities == []
        assert data.google_docs == []
        assert data.whoop_recovery is None

        # All errors should be in metadata
        assert "apple_calendar_error" in data.metadata
        assert "github_error" in data.metadata
        assert "atlassian_error" in data.metadata
        assert "things_error" in data.metadata
        assert "wakatime_error" in data.metadata
        assert "google_docs_error" in data.metadata
        assert "whoop_error" in data.metadata
