"""Tests for GitHub PyGithub migration."""

from datetime import UTC, date, datetime
from unittest.mock import Mock, patch

import pytest

from pkm_tool.sources.github import fetch_github_activities


@pytest.fixture
def mock_github_client() -> Mock:
    """Create a mock GitHub client."""
    return Mock()


@pytest.fixture
def mock_authenticated_user() -> Mock:
    """Create a mock authenticated user."""
    user = Mock()
    user.login = "testuser"
    return user


@pytest.fixture
def sample_config() -> dict[str, str]:
    """Sample configuration with token."""
    return {"token": "test_token_123"}


class TestFetchGitHubActivities:
    """Test suite for fetch_github_activities function."""

    def test_fetch_with_no_token_returns_empty_list(self) -> None:
        """Test that missing token returns empty list."""
        target_date = date(2025, 11, 21)
        config = {}  # No token

        activities = fetch_github_activities(target_date, config)

        assert activities == []

    def test_fetch_with_empty_events_returns_empty_list(
        self,
        mock_github_client: Mock,
        mock_authenticated_user: Mock,
        sample_config: dict[str, str],
    ) -> None:
        """Test that no events returns empty list."""
        target_date = date(2025, 11, 21)

        # Mock empty events
        mock_github_client.get_user.return_value = mock_authenticated_user
        mock_authenticated_user.get_events.return_value = []

        with patch("pkm_tool.sources.github.Github", return_value=mock_github_client):
            activities = fetch_github_activities(target_date, sample_config)

        assert activities == []

    def test_fetch_filters_by_target_date(
        self,
        mock_github_client: Mock,
        mock_authenticated_user: Mock,
        sample_config: dict[str, str],
    ) -> None:
        """Test that only events from target date are returned."""
        target_date = date(2025, 11, 21)

        # Create events with different dates
        event1 = Mock()
        event1.type = "PushEvent"
        event1.created_at = datetime(2025, 11, 21, 10, 0, tzinfo=UTC)
        event1.repo.name = "test/repo1"
        event1.payload = {"size": 2}

        event2 = Mock()
        event2.type = "PushEvent"
        event2.created_at = datetime(2025, 11, 20, 10, 0, tzinfo=UTC)  # Different date
        event2.repo.name = "test/repo2"
        event2.payload = {"size": 1}

        mock_github_client.get_user.return_value = mock_authenticated_user
        mock_authenticated_user.get_events.return_value = [event1, event2]

        with patch("pkm_tool.sources.github.Github", return_value=mock_github_client):
            activities = fetch_github_activities(target_date, sample_config)

        # Only event1 should be returned
        assert len(activities) == 1
        assert activities[0].repository == "test/repo1"

    def test_fetch_maps_push_event_to_commit(
        self,
        mock_github_client: Mock,
        mock_authenticated_user: Mock,
        sample_config: dict[str, str],
    ) -> None:
        """Test PushEvent is mapped to commit GitHubActivity."""
        target_date = date(2025, 11, 21)

        # Create PushEvent
        event = Mock()
        event.type = "PushEvent"
        event.created_at = datetime(2025, 11, 21, 14, 30, tzinfo=UTC)
        event.repo.name = "owner/repository"
        event.payload = {"size": 3}

        mock_github_client.get_user.return_value = mock_authenticated_user
        mock_authenticated_user.get_events.return_value = [event]

        with patch("pkm_tool.sources.github.Github", return_value=mock_github_client):
            activities = fetch_github_activities(target_date, sample_config)

        assert len(activities) == 1
        activity = activities[0]
        assert activity.type == "commit"
        assert activity.title == "Pushed 3 commits"
        assert activity.url == "https://github.com/owner/repository"
        assert activity.repository == "owner/repository"
        assert activity.timestamp == datetime(2025, 11, 21, 14, 30, tzinfo=UTC)
        assert activity.details is None

    def test_fetch_maps_pull_request_event_to_pr(
        self,
        mock_github_client: Mock,
        mock_authenticated_user: Mock,
        sample_config: dict[str, str],
    ) -> None:
        """Test PullRequestEvent is mapped to pr GitHubActivity."""
        target_date = date(2025, 11, 21)

        # Create PullRequestEvent
        event = Mock()
        event.type = "PullRequestEvent"
        event.created_at = datetime(2025, 11, 21, 15, 45, tzinfo=UTC)
        event.repo.name = "owner/repo"
        event.payload = {
            "action": "opened",
            "pull_request": {
                "title": "Add new feature",
                "html_url": "https://github.com/owner/repo/pull/42",
            },
        }

        mock_github_client.get_user.return_value = mock_authenticated_user
        mock_authenticated_user.get_events.return_value = [event]

        with patch("pkm_tool.sources.github.Github", return_value=mock_github_client):
            activities = fetch_github_activities(target_date, sample_config)

        assert len(activities) == 1
        activity = activities[0]
        assert activity.type == "pr"
        assert activity.title == "Add new feature"
        assert activity.url == "https://github.com/owner/repo/pull/42"
        assert activity.repository == "owner/repo"
        assert activity.details == "Action: opened"

    def test_fetch_maps_issues_event_to_issue(
        self,
        mock_github_client: Mock,
        mock_authenticated_user: Mock,
        sample_config: dict[str, str],
    ) -> None:
        """Test IssuesEvent is mapped to issue GitHubActivity."""
        target_date = date(2025, 11, 21)

        # Create IssuesEvent
        event = Mock()
        event.type = "IssuesEvent"
        event.created_at = datetime(2025, 11, 21, 9, 15, tzinfo=UTC)
        event.repo.name = "owner/repo"
        event.payload = {
            "action": "opened",
            "issue": {
                "title": "Bug report",
                "html_url": "https://github.com/owner/repo/issues/100",
            },
        }

        mock_github_client.get_user.return_value = mock_authenticated_user
        mock_authenticated_user.get_events.return_value = [event]

        with patch("pkm_tool.sources.github.Github", return_value=mock_github_client):
            activities = fetch_github_activities(target_date, sample_config)

        assert len(activities) == 1
        activity = activities[0]
        assert activity.type == "issue"
        assert activity.title == "Bug report"
        assert activity.url == "https://github.com/owner/repo/issues/100"
        assert activity.repository == "owner/repo"
        assert activity.details == "Action: opened"

    def test_fetch_maps_pull_request_review_event_to_review(
        self,
        mock_github_client: Mock,
        mock_authenticated_user: Mock,
        sample_config: dict[str, str],
    ) -> None:
        """Test PullRequestReviewEvent is mapped to review GitHubActivity."""
        target_date = date(2025, 11, 21)

        # Create PullRequestReviewEvent
        event = Mock()
        event.type = "PullRequestReviewEvent"
        event.created_at = datetime(2025, 11, 21, 16, 30, tzinfo=UTC)
        event.repo.name = "owner/repo"
        event.payload = {
            "pull_request": {
                "title": "Fix bug in auth",
                "html_url": "https://github.com/owner/repo/pull/55",
            }
        }

        mock_github_client.get_user.return_value = mock_authenticated_user
        mock_authenticated_user.get_events.return_value = [event]

        with patch("pkm_tool.sources.github.Github", return_value=mock_github_client):
            activities = fetch_github_activities(target_date, sample_config)

        assert len(activities) == 1
        activity = activities[0]
        assert activity.type == "review"
        assert activity.title == "Fix bug in auth"
        assert activity.url == "https://github.com/owner/repo/pull/55"
        assert activity.repository == "owner/repo"
        assert activity.details == "Reviewed PR"

    def test_fetch_ignores_unknown_event_types(
        self,
        mock_github_client: Mock,
        mock_authenticated_user: Mock,
        sample_config: dict[str, str],
    ) -> None:
        """Test that unknown event types are ignored."""
        target_date = date(2025, 11, 21)

        # Create unknown event type
        event1 = Mock()
        event1.type = "UnknownEventType"
        event1.created_at = datetime(2025, 11, 21, 10, 0, tzinfo=UTC)

        # Create known event type for comparison
        event2 = Mock()
        event2.type = "PushEvent"
        event2.created_at = datetime(2025, 11, 21, 11, 0, tzinfo=UTC)
        event2.repo.name = "test/repo"
        event2.payload = {"size": 1}

        mock_github_client.get_user.return_value = mock_authenticated_user
        mock_authenticated_user.get_events.return_value = [event1, event2]

        with patch("pkm_tool.sources.github.Github", return_value=mock_github_client):
            activities = fetch_github_activities(target_date, sample_config)

        # Only event2 should be returned
        assert len(activities) == 1
        assert activities[0].repository == "test/repo"

    def test_fetch_handles_multiple_events_same_date(
        self,
        mock_github_client: Mock,
        mock_authenticated_user: Mock,
        sample_config: dict[str, str],
    ) -> None:
        """Test that multiple events from same date are all returned."""
        target_date = date(2025, 11, 21)

        # Create multiple events
        event1 = Mock()
        event1.type = "PushEvent"
        event1.created_at = datetime(2025, 11, 21, 10, 0, tzinfo=UTC)
        event1.repo.name = "test/repo1"
        event1.payload = {"size": 1}

        event2 = Mock()
        event2.type = "IssuesEvent"
        event2.created_at = datetime(2025, 11, 21, 14, 0, tzinfo=UTC)
        event2.repo.name = "test/repo2"
        event2.payload = {
            "action": "closed",
            "issue": {"title": "Test issue", "html_url": "https://github.com/test/repo2/issues/1"},
        }

        event3 = Mock()
        event3.type = "PullRequestEvent"
        event3.created_at = datetime(2025, 11, 21, 18, 0, tzinfo=UTC)
        event3.repo.name = "test/repo3"
        event3.payload = {
            "action": "merged",
            "pull_request": {
                "title": "Test PR",
                "html_url": "https://github.com/test/repo3/pull/1",
            },
        }

        mock_github_client.get_user.return_value = mock_authenticated_user
        mock_authenticated_user.get_events.return_value = [event1, event2, event3]

        with patch("pkm_tool.sources.github.Github", return_value=mock_github_client):
            activities = fetch_github_activities(target_date, sample_config)

        assert len(activities) == 3
        assert activities[0].type == "commit"
        assert activities[1].type == "issue"
        assert activities[2].type == "pr"

    def test_fetch_handles_github_api_error_gracefully(self, sample_config: dict[str, str]) -> None:
        """Test that GitHub API errors return empty list."""
        target_date = date(2025, 11, 21)

        # Mock Github to raise exception
        with patch("pkm_tool.sources.github.Github", side_effect=Exception("API Error")):
            activities = fetch_github_activities(target_date, sample_config)

        assert activities == []

    def test_fetch_handles_auth_error_gracefully(self, sample_config: dict[str, str]) -> None:
        """Test that authentication errors return empty list."""
        target_date = date(2025, 11, 21)

        # Mock Github.get_user to raise exception
        with patch("pkm_tool.sources.github.Github") as mock_github:
            mock_github.return_value.get_user.side_effect = Exception("Auth failed")
            activities = fetch_github_activities(target_date, sample_config)

        assert activities == []

    def test_fetch_reads_token_from_environment(
        self,
        mock_github_client: Mock,
        mock_authenticated_user: Mock,
    ) -> None:
        """Test that token is correctly read from environment variable."""
        target_date = date(2025, 11, 21)
        config = {}  # No token in config

        mock_github_client.get_user.return_value = mock_authenticated_user
        mock_authenticated_user.get_events.return_value = []

        with (
            patch("pkm_tool.sources.github.Github", return_value=mock_github_client),
            patch("os.getenv", return_value="test_token_from_env"),
        ):
            activities = fetch_github_activities(target_date, config)

            # Should not raise error and should try to fetch events
            assert activities == []

    def test_fetch_handles_malformed_event_data(
        self,
        mock_github_client: Mock,
        mock_authenticated_user: Mock,
        sample_config: dict[str, str],
    ) -> None:
        """Test that malformed event data is handled gracefully."""
        target_date = date(2025, 11, 21)

        # Create event with missing payload data
        event = Mock()
        event.type = "PushEvent"
        event.created_at = datetime(2025, 11, 21, 10, 0, tzinfo=UTC)
        event.repo.name = "test/repo"
        event.payload = {}  # Missing 'size' key

        mock_github_client.get_user.return_value = mock_authenticated_user
        mock_authenticated_user.get_events.return_value = [event]

        with patch("pkm_tool.sources.github.Github", return_value=mock_github_client):
            activities = fetch_github_activities(target_date, sample_config)

        # Should handle gracefully - either skip event or use default value
        # Implementation will use .get() with default value
        assert len(activities) == 1
        assert "Pushed 0 commits" in activities[0].title  # Default size is 0
