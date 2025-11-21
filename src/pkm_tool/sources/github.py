"""GitHub integration using PyGithub library."""

import os
from datetime import date
from typing import Any

import structlog
from github import Auth, Github, GithubException

from pkm_tool.auth import AuthManager
from pkm_tool.models import GitHubActivity

logger = structlog.get_logger(__name__)
_AUTH_MANAGER = AuthManager()


def fetch_github_activities(target_date: date, config: dict[str, Any]) -> list[GitHubActivity]:
    """
    Fetch GitHub activities for a given date using PyGithub library.

    Args:
        target_date: Date to fetch activities for
        config: Configuration dictionary with optional 'token'

    Returns:
        List of GitHubActivity objects
    """
    logger.debug("github_fetch_started", date=str(target_date), using_pygithub=True)
    try:
        activities = _fetch_github_via_pygithub(target_date, config)
        logger.info("github_activities_fetched", activity_count=len(activities))
        return activities
    except Exception as e:
        # All exceptions are caught and return empty list
        # This ensures graceful degradation
        logger.error("github_fetch_failed", error=str(e), exc_info=True)
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
        # Get token from token store first, then config/env fallback
        token = _get_github_token(config)
        if not token:
            logger.warning("github_no_token", message="No GitHub token configured")
            return []

        # Authenticate with GitHub
        logger.debug("github_authenticating")
        auth = Auth.Token(token)
        g = Github(auth=auth)
        # Get authenticated user
        user = g.get_user()
        logger.info("github_authenticated", username=user.login)

        # Fetch user events (GitHub provides last 90 days)
        logger.debug("github_fetching_events", username=user.login, date=str(target_date))
        events = user.get_events()

        # Filter and map events to GitHubActivity
        activities = []
        event_count = 0
        for event in events:
            event_count += 1
            # Filter by target date
            if event.created_at.date() != target_date:
                continue

            # Map event to GitHubActivity based on type
            activity = _map_event_to_activity(event)
            if activity:
                activities.append(activity)

        logger.debug(
            "github_events_processed",
            total_events=event_count,
            matched_events=len(activities),
            date=str(target_date),
        )
        return activities

    except GithubException as e:
        # GitHub API errors (auth, rate limit, etc.)
        logger.error("github_api_error", error=str(e), status=getattr(e, "status", None))
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


def _get_github_token(config: dict[str, Any]) -> str | None:
    """Retrieve GitHub token from token store or fall back to config/env."""
    stored = _AUTH_MANAGER.get_token("github")
    if stored:
        return stored.token
    return config.get("token") or os.getenv("GITHUB_TOKEN")
