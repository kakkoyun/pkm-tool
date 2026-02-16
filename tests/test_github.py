"""Tests for GitHub source module."""

from datetime import date
from unittest.mock import Mock

from github import GithubException

from pkm_tool.sources.github import (
    _get_github_token,
    _map_event_to_activity,
    fetch_github_activities,
)

TARGET_DATE = date(2025, 11, 21)


class TestFetchGithubActivities:
    """Test main fetch function."""

    def test_fetch_all_event_types(self, mock_github_client, mock_github_auth, mocker):
        """Fetch activities returns all supported event types."""
        mocker.patch("pkm_tool.sources.github.get_source_token", return_value="test-token")
        activities = fetch_github_activities(TARGET_DATE, {})
        assert len(activities) == 4
        types = {a.type for a in activities}
        assert types == {"commit", "pr", "issue", "review"}

    def test_fetch_returns_empty_on_no_token(self, mocker):
        """Returns empty list when no token is available."""
        mocker.patch("pkm_tool.sources.github.get_source_token", return_value=None)
        activities = fetch_github_activities(TARGET_DATE, {})
        assert activities == []

    def test_fetch_returns_empty_on_github_exception(self, mocker):
        """Returns empty list on GithubException."""
        mocker.patch("pkm_tool.sources.github.get_source_token", return_value="test-token")
        mock_github = mocker.patch("pkm_tool.sources.github.Github")
        mock_github.return_value.get_user.side_effect = GithubException(
            401, {"message": "Bad credentials"}, {}
        )
        mock_github.return_value.close = Mock()
        activities = fetch_github_activities(TARGET_DATE, {})
        assert activities == []

    def test_fetch_returns_empty_on_unexpected_exception(self, mocker):
        """Returns empty list on unexpected exceptions."""
        mocker.patch("pkm_tool.sources.github.get_source_token", return_value="test-token")
        mock_github = mocker.patch("pkm_tool.sources.github.Github")
        mock_github.return_value.get_user.side_effect = RuntimeError("unexpected")
        mock_github.return_value.close = Mock()
        activities = fetch_github_activities(TARGET_DATE, {})
        assert activities == []

    def test_fetch_filters_by_date(self, mock_github_auth, mocker):
        """Only returns events matching target date."""
        mocker.patch("pkm_tool.sources.github.get_source_token", return_value="test-token")
        # Create events on wrong date
        from datetime import UTC, datetime

        wrong_date_event = Mock()
        wrong_date_event.type = "PushEvent"
        wrong_date_event.created_at = datetime(2025, 11, 20, 10, 0, tzinfo=UTC)
        wrong_date_event.repo = Mock()
        wrong_date_event.repo.name = "testuser/repo"
        wrong_date_event.payload = {"size": 1}
        wrong_date_event.actor = Mock()
        wrong_date_event.actor.login = "testuser"

        user = Mock()
        user.login = "testuser"
        user.get_events.return_value = [wrong_date_event]

        mock_github = mocker.patch("pkm_tool.sources.github.Github")
        mock_github.return_value.get_user.return_value = user
        mock_github.return_value.close = Mock()

        activities = fetch_github_activities(TARGET_DATE, {})
        assert activities == []

    def test_github_client_always_closed(self, mock_github_auth, mocker):
        """Github client is closed even on error."""
        mocker.patch("pkm_tool.sources.github.get_source_token", return_value="test-token")
        mock_github = mocker.patch("pkm_tool.sources.github.Github")
        mock_instance = Mock()
        mock_instance.get_user.side_effect = GithubException(500, {}, {})
        mock_github.return_value = mock_instance

        fetch_github_activities(TARGET_DATE, {})
        mock_instance.close.assert_called_once()


class TestMapEventToActivity:
    """Test event mapping function."""

    def test_push_event(self, mock_github_push_event):
        """Map PushEvent to commit activity."""
        activity = _map_event_to_activity(mock_github_push_event, "testuser")
        assert activity is not None
        assert activity.type == "commit"
        assert "3 commits" in activity.title
        assert activity.repository == "testuser/test-repo"

    def test_pr_event_opened(self, mock_github_pr_event):
        """Map PullRequestEvent (opened) to pr activity."""
        activity = _map_event_to_activity(mock_github_pr_event, "testuser")
        assert activity is not None
        assert activity.type == "pr"
        assert activity.title == "Add new feature"
        assert activity.details is not None
        assert "Action: opened" in activity.details

    def test_pr_event_filtered_action(self):
        """PR events with passive actions should be filtered."""
        event = Mock()
        event.type = "PullRequestEvent"
        event.created_at = Mock()
        event.repo = Mock()
        event.repo.name = "user/repo"
        event.payload = {"action": "assigned", "pull_request": {"title": "PR"}}
        event.actor = Mock()
        event.actor.login = "testuser"
        assert _map_event_to_activity(event, "testuser") is None

    def test_issue_event_opened(self, mock_github_issue_event):
        """Map IssuesEvent (opened) to issue activity."""
        activity = _map_event_to_activity(mock_github_issue_event, "testuser")
        assert activity is not None
        assert activity.type == "issue"
        assert activity.title == "Fix critical bug"

    def test_issue_event_filtered_action(self):
        """Issue events with passive actions should be filtered."""
        event = Mock()
        event.type = "IssuesEvent"
        event.created_at = Mock()
        event.repo = Mock()
        event.repo.name = "user/repo"
        event.payload = {"action": "labeled", "issue": {"title": "Issue"}}
        event.actor = Mock()
        event.actor.login = "testuser"
        assert _map_event_to_activity(event, "testuser") is None

    def test_review_event(self, mock_github_review_event):
        """Map PullRequestReviewEvent to review activity."""
        activity = _map_event_to_activity(mock_github_review_event, "testuser")
        assert activity is not None
        assert activity.type == "review"
        assert activity.details is not None
        assert "Reviewed PR" in activity.details

    def test_unknown_event_type(self):
        """Unknown event types should return None."""
        event = Mock()
        event.type = "WatchEvent"
        event.actor = Mock()
        event.actor.login = "testuser"
        assert _map_event_to_activity(event, "testuser") is None

    def test_different_actor_filtered(self):
        """Events from different actors should be filtered."""
        event = Mock()
        event.type = "PushEvent"
        event.actor = Mock()
        event.actor.login = "otheruser"
        assert _map_event_to_activity(event, "testuser") is None

    def test_malformed_event_data(self):
        """Malformed event data should return None instead of raising."""
        event = Mock()
        event.type = "PushEvent"
        event.actor = Mock()
        event.actor.login = "testuser"
        event.repo = Mock()
        event.repo.name = "user/repo"
        event.created_at = Mock()
        # payload.get will raise on bad data
        event.payload = None  # Will cause AttributeError on .get()
        # The function catches KeyError and AttributeError
        result = _map_event_to_activity(event, "testuser")
        assert result is None


class TestGetGithubToken:
    """Test token retrieval."""

    def test_token_from_config(self, mocker):
        """Token retrieved from config."""
        mocker.patch("pkm_tool.sources.github.get_source_token", return_value="config-token")
        token = _get_github_token({"token": "config-token"})
        assert token == "config-token"

    def test_no_token_returns_none(self, mocker):
        """Returns None when no token available."""
        mocker.patch("pkm_tool.sources.github.get_source_token", return_value=None)
        token = _get_github_token({})
        assert token is None
