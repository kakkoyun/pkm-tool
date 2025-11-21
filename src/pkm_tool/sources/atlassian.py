"""Atlassian (Jira/Confluence) integration."""

import os
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from pkm_tool.models import AtlassianItem


def fetch_atlassian_items(target_date: date, config: dict[str, Any]) -> list[AtlassianItem]:
    """
    Fetch Jira issues and Confluence pages updated on target date.

    Args:
        target_date: Date to fetch items for
        config: Configuration dictionary with 'base_url', 'username', 'api_token'

    Returns:
        List of AtlassianItem objects
    """
    base_url = config.get("base_url", os.environ.get("ATLASSIAN_BASE_URL"))
    username = config.get("username", os.environ.get("ATLASSIAN_USERNAME"))
    api_token = config.get("api_token", os.environ.get("ATLASSIAN_API_TOKEN"))

    if not all([base_url, username, api_token]):
        return []

    items = []

    # Fetch Jira issues
    jira_items = _fetch_jira_issues(target_date, base_url, username, api_token)
    items.extend(jira_items)

    # Fetch Confluence pages
    confluence_items = _fetch_confluence_pages(target_date, base_url, username, api_token)
    items.extend(confluence_items)

    return items


def _fetch_jira_issues(
    target_date: date, base_url: str, username: str, api_token: str
) -> list[AtlassianItem]:
    """Fetch Jira issues updated on target date."""
    items = []

    # JQL query for issues updated on target date
    jql = f'updated >= "{target_date}" AND updated < "{target_date + timedelta(days=1)}"'

    try:
        with httpx.Client(auth=(username, api_token), timeout=30.0) as client:
            response = client.get(
                f"{base_url}/rest/api/3/search",
                params={"jql": jql, "maxResults": 100},
            )
            response.raise_for_status()
            data = response.json()

            for issue in data.get("issues", []):
                item = AtlassianItem(
                    type="jira_issue",
                    title=issue["fields"]["summary"],
                    url=f"{base_url}/browse/{issue['key']}",
                    key=issue["key"],
                    status=issue["fields"]["status"]["name"],
                    updated=datetime.fromisoformat(
                        issue["fields"]["updated"].replace("Z", "+00:00")
                    ),
                )
                items.append(item)
    except (httpx.HTTPError, KeyError):
        pass

    return items


def _fetch_confluence_pages(
    target_date: date, base_url: str, username: str, api_token: str
) -> list[AtlassianItem]:
    """Fetch Confluence pages updated on target date."""
    items = []

    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())

    try:
        with httpx.Client(auth=(username, api_token), timeout=30.0) as client:
            # CQL query for pages updated on target date
            start_iso = start_datetime.isoformat()
            end_iso = end_datetime.isoformat()
            cql = f'lastModified >= "{start_iso}" AND lastModified <= "{end_iso}"'

            response = client.get(
                f"{base_url}/wiki/rest/api/content/search",
                params={"cql": cql, "limit": 100},
            )
            response.raise_for_status()
            data = response.json()

            for page in data.get("results", []):
                item = AtlassianItem(
                    type="confluence_page",
                    title=page["title"],
                    url=f"{base_url}/wiki{page['_links']['webui']}",
                    key=page["id"],
                    status=None,
                    updated=datetime.fromisoformat(
                        page["history"]["lastUpdated"]["when"].replace("Z", "+00:00")
                    ),
                )
                items.append(item)
    except (httpx.HTTPError, KeyError):
        pass

    return items
