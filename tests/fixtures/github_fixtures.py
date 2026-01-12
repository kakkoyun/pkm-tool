"""GitHub API mock fixtures."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_github_push_event() -> Mock:
    """Create a mock GitHub PushEvent."""
    event = Mock()
    event.type = "PushEvent"
    event.created_at = datetime(2025, 11, 21, 10, 30, tzinfo=UTC)
    event.repo = Mock()
    event.repo.name = "testuser/test-repo"
    event.payload = {"size": 3}
    # Add actor property for filtering
    event.actor = Mock()
    event.actor.login = "testuser"
    return event


@pytest.fixture
def mock_github_pr_event() -> Mock:
    """Create a mock GitHub PullRequestEvent."""
    event = Mock()
    event.type = "PullRequestEvent"
    event.created_at = datetime(2025, 11, 21, 14, 15, tzinfo=UTC)
    event.repo = Mock()
    event.repo.name = "testuser/awesome-project"
    event.payload = {
        "action": "opened",
        "pull_request": {
            "title": "Add new feature",
            "html_url": "https://github.com/testuser/awesome-project/pull/42",
        },
    }
    # Add actor property for filtering
    event.actor = Mock()
    event.actor.login = "testuser"
    return event


@pytest.fixture
def mock_github_issue_event() -> Mock:
    """Create a mock GitHub IssuesEvent."""
    event = Mock()
    event.type = "IssuesEvent"
    event.created_at = datetime(2025, 11, 21, 9, 0, tzinfo=UTC)
    event.repo = Mock()
    event.repo.name = "testuser/bug-tracker"
    event.payload = {
        "action": "opened",
        "issue": {
            "title": "Fix critical bug",
            "html_url": "https://github.com/testuser/bug-tracker/issues/123",
        },
    }
    # Add actor property for filtering
    event.actor = Mock()
    event.actor.login = "testuser"
    return event


@pytest.fixture
def mock_github_review_event() -> Mock:
    """Create a mock GitHub PullRequestReviewEvent."""
    event = Mock()
    event.type = "PullRequestReviewEvent"
    event.created_at = datetime(2025, 11, 21, 16, 45, tzinfo=UTC)
    event.repo = Mock()
    event.repo.name = "testuser/code-review"
    event.payload = {
        "pull_request": {
            "title": "Update documentation",
            "html_url": "https://github.com/testuser/code-review/pull/5",
        }
    }
    # Add actor property for filtering
    event.actor = Mock()
    event.actor.login = "testuser"
    return event


@pytest.fixture
def mock_github_events(
    mock_github_push_event: Mock,
    mock_github_pr_event: Mock,
    mock_github_issue_event: Mock,
    mock_github_review_event: Mock,
) -> list[Mock]:
    """Create a list of mock GitHub events."""
    return [
        mock_github_push_event,
        mock_github_pr_event,
        mock_github_issue_event,
        mock_github_review_event,
    ]


@pytest.fixture
def mock_github_user(mock_github_events: list[Mock]) -> Mock:
    """Create a mock GitHub user with events."""
    user = Mock()
    user.get_events.return_value = mock_github_events
    user.login = "testuser"
    return user


@pytest.fixture
def mock_github_client(mocker: Mock, mock_github_user: Mock) -> Mock:
    """Mock the PyGithub Github client."""
    mock_github = mocker.patch("pkm_tool.sources.github.Github")
    mock_instance = Mock()
    mock_instance.get_user.return_value = mock_github_user
    mock_instance.close = Mock()
    mock_github.return_value = mock_instance
    return mock_instance


@pytest.fixture
def mock_github_auth(mocker: Mock) -> Mock:
    """Mock the PyGithub Auth.Token."""
    mock_auth = mocker.patch("pkm_tool.sources.github.Auth.Token")
    return mock_auth
