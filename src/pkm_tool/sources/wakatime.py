"""Wakatime integration."""

import os
from datetime import date
from typing import Any

import httpx
import structlog

from pkm_tool.auth import AuthManager
from pkm_tool.cache import get_cached_client
from pkm_tool.config import CacheConfig
from pkm_tool.models import WakatimeActivity

logger = structlog.get_logger(__name__)
_AUTH_MANAGER = AuthManager()


def fetch_wakatime_activities(
    target_date: date,
    config: dict[str, Any],
    cache_config: CacheConfig | None = None,
) -> list[WakatimeActivity]:
    """
    Fetch Wakatime coding activities for a given date.

    Args:
        target_date: Date to fetch activities for
        config: Configuration dictionary with 'api_key'
        cache_config: Optional cache configuration for HTTP response caching

    Returns:
        List of WakatimeActivity objects (per project)
    """
    logger.debug("wakatime_fetch_started", date=str(target_date))
    api_key = _get_wakatime_token(config)

    if not api_key:
        logger.warning("wakatime_no_token", message="No Wakatime API key configured")
        return []

    activities: list[WakatimeActivity] = []

    try:
        logger.debug("wakatime_fetching_summaries", date=str(target_date))
        headers = {"Authorization": f"Bearer {api_key}"}

        # Use cached client if cache config provided, otherwise regular httpx client
        if cache_config:
            client = get_cached_client(cache_config, headers=headers, timeout=30.0)
        else:
            client = httpx.Client(headers=headers, timeout=30.0)

        with client:
            # Fetch summaries for the target date
            date_str = target_date.strftime("%Y-%m-%d")
            response = client.get(
                "https://wakatime.com/api/v1/users/current/summaries",
                params={"start": date_str, "end": date_str},
            )
            response.raise_for_status()
            data = response.json()

            # Parse summaries
            for day in data.get("data", []):
                for project in day.get("projects", []):
                    activity = WakatimeActivity(
                        project=project["name"],
                        duration_seconds=int(project["total_seconds"]),
                        language=None,
                    )
                    activities.append(activity)

                # Also get language information
                language_map: dict[str, int] = {}
                for language in day.get("languages", []):
                    language_map[language["name"]] = int(language["total_seconds"])

                # Try to match languages to projects (approximate)
                # In reality, Wakatime doesn't provide per-project language breakdown easily
                # This is a simplified version
                for activity in activities:
                    # Get most used language for the day as a proxy
                    if language_map:
                        most_used_lang = max(language_map.items(), key=lambda x: x[1])[0]
                        activity.language = most_used_lang

        logger.info("wakatime_activities_fetched", activity_count=len(activities))

    except (httpx.HTTPError, KeyError) as e:
        # All exceptions are caught and return empty list
        # This ensures graceful degradation
        logger.error("wakatime_fetch_failed", error=str(e), exc_info=True)

    return activities


def _get_wakatime_token(config: dict[str, Any]) -> str | None:
    """Retrieve Wakatime API key from token store or fall back to config/env."""
    stored = _AUTH_MANAGER.get_token("wakatime")
    if stored:
        return stored.token
    return config.get("api_key") or os.environ.get("WAKATIME_API_KEY")
