"""GitHub integration."""

import json
import os
import subprocess
from datetime import date, datetime
from typing import Any

import httpx

from pkm_tool.models import GitHubActivity


def fetch_github_activities(target_date: date, config: dict[str, Any]) -> list[GitHubActivity]:
    """
    Fetch GitHub activities for a given date.

    Can use either GitHub token or gh CLI.

    Args:
        target_date: Date to fetch activities for
        config: Configuration dictionary with optional 'token' or 'use_gh_cli'

    Returns:
        List of GitHubActivity objects
    """
    use_gh_cli = config.get("use_gh_cli", True)
    token = config.get("token", os.environ.get("GITHUB_TOKEN"))
    username = config.get("username", os.environ.get("GITHUB_USERNAME"))

    if use_gh_cli:
        return _fetch_via_gh_cli(target_date, username)
    elif token and username:
        return _fetch_via_api(target_date, username, token)
    else:
        raise ValueError("GitHub configuration requires either gh CLI or token + username")


def _fetch_via_gh_cli(target_date: date, username: str | None) -> list[GitHubActivity]:
    """Fetch activities using gh CLI."""
    try:
        # Check if gh is available
        subprocess.run(["gh", "--version"], capture_output=True, check=True, timeout=5)
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

    activities = []

    # Get current user if username not provided
    if not username:
        try:
            result = subprocess.run(
                ["gh", "api", "user", "--jq", ".login"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            username = result.stdout.strip()
        except subprocess.SubprocessError:
            return []

    # Fetch recent events
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())

    try:
        # Get user events
        result = subprocess.run(
            ["gh", "api", f"users/{username}/events", "--paginate"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        events = json.loads(result.stdout)

        for event in events:
            created_at = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))

            # Filter by date
            if not (start_datetime <= created_at <= end_datetime):
                continue

            # Parse different event types
            if event["type"] == "PushEvent":
                activity = GitHubActivity(
                    type="commit",
                    title=f"Pushed {event['payload'].get('size', 0)} commits",
                    url=f"https://github.com/{event['repo']['name']}",
                    repository=event["repo"]["name"],
                    timestamp=created_at,
                    details=None,
                )
                activities.append(activity)
            elif event["type"] == "PullRequestEvent":
                pr = event["payload"]["pull_request"]
                activity = GitHubActivity(
                    type="pr",
                    title=pr["title"],
                    url=pr["html_url"],
                    repository=event["repo"]["name"],
                    timestamp=created_at,
                    details=f"Action: {event['payload']['action']}",
                )
                activities.append(activity)
            elif event["type"] == "IssuesEvent":
                issue = event["payload"]["issue"]
                activity = GitHubActivity(
                    type="issue",
                    title=issue["title"],
                    url=issue["html_url"],
                    repository=event["repo"]["name"],
                    timestamp=created_at,
                    details=f"Action: {event['payload']['action']}",
                )
                activities.append(activity)
            elif event["type"] == "PullRequestReviewEvent":
                pr = event["payload"]["pull_request"]
                activity = GitHubActivity(
                    type="review",
                    title=pr["title"],
                    url=pr["html_url"],
                    repository=event["repo"]["name"],
                    timestamp=created_at,
                    details="Reviewed PR",
                )
                activities.append(activity)

        return activities
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return []


def _fetch_via_api(target_date: date, username: str, token: str) -> list[GitHubActivity]:
    """Fetch activities using GitHub API directly."""
    activities = []
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())

    try:
        with httpx.Client(headers=headers, timeout=30.0) as client:
            response = client.get(f"https://api.github.com/users/{username}/events")
            response.raise_for_status()
            events = response.json()

            for event in events:
                created_at = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))

                # Filter by date
                if not (start_datetime <= created_at <= end_datetime):
                    continue

                # Parse different event types (similar to gh CLI parsing)
                if event["type"] == "PushEvent":
                    activity = GitHubActivity(
                        type="commit",
                        title=f"Pushed {event['payload'].get('size', 0)} commits",
                        url=f"https://github.com/{event['repo']['name']}",
                        repository=event["repo"]["name"],
                        timestamp=created_at,
                        details=None,
                    )
                    activities.append(activity)
                # Add other event types as needed

        return activities
    except (httpx.HTTPError, KeyError):
        return []
