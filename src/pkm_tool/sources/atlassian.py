"""Atlassian (Jira/Confluence) integration."""

import json
import os
from datetime import date, datetime, timedelta
from typing import Any

import structlog
from atlassian import Confluence, Jira  # type: ignore

from pkm_tool.auth import AuthManager
from pkm_tool.models import AtlassianItem

logger = structlog.get_logger(__name__)
_AUTH_MANAGER = AuthManager()


def fetch_atlassian_items(target_date: date, config: dict[str, Any]) -> list[AtlassianItem]:
    """
    Fetch Jira issues and Confluence pages updated on target date.

    Args:
        target_date: Date to fetch items for
        config: Configuration dictionary with 'base_url', 'username', 'api_token'

    Returns:
        List of AtlassianItem objects
    """
    base_url, username, api_token = _get_atlassian_credentials(config)

    if not all([base_url, username, api_token]):
        logger.warning(
            "atlassian_config_incomplete",
            has_url=bool(base_url),
            has_username=bool(username),
            has_token=bool(api_token),
        )
        return []

    if not base_url or not username or not api_token:
        logger.warning(
            "atlassian_credentials_missing",
            has_base_url=bool(base_url),
            has_username=bool(username),
            has_token=bool(api_token),
        )
        return []

    logger.debug("atlassian_fetching_items", date=str(target_date), base_url=base_url)
    try:
        jira_items = _fetch_jira_via_library(target_date, base_url, username, api_token)
        logger.info("atlassian_jira_fetched", item_count=len(jira_items))
        confluence_items = _fetch_confluence_via_library(target_date, base_url, username, api_token)
        logger.info("atlassian_confluence_fetched", item_count=len(confluence_items))
        total_items = jira_items + confluence_items
        logger.info("atlassian_total_items", item_count=len(total_items))
        return total_items
    except Exception as e:
        # Graceful degradation - return empty list on any error
        logger.error("atlassian_fetch_failed", error=str(e), exc_info=True)
        return []


def _fetch_jira_via_library(
    target_date: date, base_url: str, username: str, api_token: str
) -> list[AtlassianItem]:
    """Fetch Jira issues updated on target date using atlassian-python-api."""
    items = []

    try:
        # Initialize Jira client
        logger.debug("jira_initializing_client", base_url=base_url)
        jira = Jira(url=base_url, username=username, password=api_token, cloud=True)

        # JQL query for issues updated on target date
        # Use date range to capture entire day
        start_date = target_date.isoformat()
        end_date = (target_date + timedelta(days=1)).isoformat()
        jql = f'updated >= "{start_date}" AND updated < "{end_date}"'
        logger.debug("jira_query", jql=jql)

        # Execute JQL query
        results = jira.jql(jql, limit=100)  # type: ignore
        logger.debug("jira_response_received", issue_count=len(results.get("issues", [])))

        # Map results to AtlassianItem models
        for issue in results.get("issues", []):
            try:
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
            except (KeyError, ValueError):
                # Skip malformed issues
                continue

    except Exception:
        # Return empty list on any error (connection, auth, etc.)
        pass

    return items


def _fetch_confluence_via_library(
    target_date: date, base_url: str, username: str, api_token: str
) -> list[AtlassianItem]:
    """Fetch Confluence pages updated on target date using atlassian-python-api."""
    items = []

    try:
        # Initialize Confluence client
        confluence = Confluence(url=base_url, username=username, password=api_token, cloud=True)

        # CQL query for pages updated on target date
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        start_iso = start_datetime.isoformat()
        end_iso = end_datetime.isoformat()
        cql = f'lastModified >= "{start_iso}" AND lastModified <= "{end_iso}"'

        # Execute CQL query
        results = confluence.cql(cql, limit=100)  # type: ignore

        # Map results to AtlassianItem models
        for page in results.get("results", []):
            try:
                item = AtlassianItem(
                    type="confluence_page",
                    title=page["title"],
                    url=f"{base_url}/wiki{page['_links']['webui']}",
                    key=page["id"],
                    status=None,  # Confluence pages don't have status like Jira
                    updated=datetime.fromisoformat(
                        page["history"]["lastUpdated"]["when"].replace("Z", "+00:00")
                    ),
                )
                items.append(item)
            except (KeyError, ValueError):
                # Skip malformed pages
                continue

    except Exception:
        # Return empty list on any error (connection, auth, etc.)
        pass

    return items


def _get_atlassian_credentials(config: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    stored = _AUTH_MANAGER.get_token("atlassian")
    if stored:
        try:
            data = json.loads(stored.token)
            return data.get("base_url"), data.get("username"), data.get("api_token")
        except json.JSONDecodeError:
            logger.error("atlassian_token_decode_failed")

    base_url = config.get("base_url", os.environ.get("ATLASSIAN_BASE_URL"))
    username = config.get("username", os.environ.get("ATLASSIAN_USERNAME"))
    api_token = config.get("api_token", os.environ.get("ATLASSIAN_API_TOKEN"))
    return base_url, username, api_token
