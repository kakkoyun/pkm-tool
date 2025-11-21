"""GitHub integration using PyGithub library."""

import os
from datetime import date
from typing import Any

from github import Auth, Github, GithubException

from pkm_tool.models import GitHubActivity


def fetch_github_activities(target_date: date, config: dict[str, Any]) -> list[GitHubActivity]:
    """
    Fetch GitHub activities for a given date using PyGithub library.

    Args:
        target_date: Date to fetch activities for
        config: Configuration dictionary with optional 'token'

    Returns:
        List of GitHubActivity objects
    """
    try:
        return _fetch_github_via_pygithub(target_date, config)
    except Exception:
        # All exceptions are caught and return empty list
        # This ensures graceful degradation
        return []


def _fetch_github_via_pygithub(target_date: date, config: dict[str, Any]) -> list[GitHubActivity]:
    """
    Internal implementation using PyGithub library.

    Args:
        target_date: Date to fetch activities for
        config: Configuration dictionary with optional 'token'

    Returns:
        List of GitHubActivity objects

    Raises:
        Exception: Any error during GitHub API interaction
    """
    g = None
    try:
        # Get token from config or environment
        token = config.get("token") or os.getenv("GITHUB_TOKEN")
        if not token:
            return []

        # Authenticate with GitHub
        auth = Auth.Token(token)
        g = Github(auth=auth)
        # Get authenticated user
        user = g.get_user()

        # Fetch user events (GitHub provides last 90 days)
        events = user.get_events()

        # Filter and map events to GitHubActivity
        activities = []
        for event in events:
            # Filter by target date
            if event.created_at.date() != target_date:
                continue

            # Map event to GitHubActivity based on type
            activity = _map_event_to_activity(event)
            if activity:
                activities.append(activity)

        return activities

    except GithubException:
        # GitHub API errors (auth, rate limit, etc.)
        return []
    finally:
        # Clean up connection
        if g is not None:
            g.close()


def _map_event_to_activity(event: Any) -> GitHubActivity | None:
    """
    Map a GitHub event to a GitHubActivity model.

    Args:
        event: PyGithub Event object

    Returns:
        GitHubActivity object or None if event type is not supported
    """
    event_type = event.type
    created_at = event.created_at
    repo_name = event.repo.name

    try:
        if event_type == "PushEvent":
            # Map PushEvent to commit activity
            size = event.payload.get("size", 0)
            return GitHubActivity(
                type="commit",
                title=f"Pushed {size} commits",
                url=f"https://github.com/{repo_name}",
                repository=repo_name,
                timestamp=created_at,
                details=None,
            )

        elif event_type == "PullRequestEvent":
            # Map PullRequestEvent to pr activity
            pr = event.payload.get("pull_request", {})
            action = event.payload.get("action", "unknown")
            return GitHubActivity(
                type="pr",
                title=pr.get("title", "Untitled PR"),
                url=pr.get("html_url", f"https://github.com/{repo_name}"),
                repository=repo_name,
                timestamp=created_at,
                details=f"Action: {action}",
            )

        elif event_type == "IssuesEvent":
            # Map IssuesEvent to issue activity
            issue = event.payload.get("issue", {})
            action = event.payload.get("action", "unknown")
            return GitHubActivity(
                type="issue",
                title=issue.get("title", "Untitled Issue"),
                url=issue.get("html_url", f"https://github.com/{repo_name}"),
                repository=repo_name,
                timestamp=created_at,
                details=f"Action: {action}",
            )

        elif event_type == "PullRequestReviewEvent":
            # Map PullRequestReviewEvent to review activity
            pr = event.payload.get("pull_request", {})
            return GitHubActivity(
                type="review",
                title=pr.get("title", "Untitled PR"),
                url=pr.get("html_url", f"https://github.com/{repo_name}"),
                repository=repo_name,
                timestamp=created_at,
                details="Reviewed PR",
            )

        else:
            # Unknown event type - skip
            return None

    except (KeyError, AttributeError):
        # Malformed event data - skip
        return None
