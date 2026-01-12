"""Wakatime integration."""

import configparser
import os
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import structlog

from pkm_tool.config import CacheConfig
from pkm_tool.models import WakatimeActivity
from pkm_tool.sources.common import create_http_client, get_source_token

logger = structlog.get_logger(__name__)


def _read_wakatime_cfg() -> str | None:
    """
    Read Wakatime API key from ~/.wakatime.cfg file.

    The .wakatime.cfg file is an INI format file with the following structure:
        [settings]
        api_key = waka_31e55b72-24d9-4572-aadd-2840000530e8

    Returns:
        API key string if found and valid, None otherwise.
    """
    cfg_path = Path.home() / ".wakatime.cfg"

    if not cfg_path.exists():
        logger.debug("wakatime_cfg_not_found", path=str(cfg_path))
        return None

    try:
        parser = configparser.ConfigParser()
        parser.read(cfg_path)

        if "settings" not in parser:
            logger.debug("wakatime_cfg_no_settings_section", path=str(cfg_path))
            return None

        api_key = parser.get("settings", "api_key", fallback=None)
        if api_key:
            logger.debug("wakatime_cfg_key_found", path=str(cfg_path))
            return api_key

        logger.debug("wakatime_cfg_no_api_key", path=str(cfg_path))
        return None

    except (configparser.Error, OSError) as e:
        # Handle malformed INI files or OS-level read errors
        logger.warning("wakatime_cfg_read_error", path=str(cfg_path), error=str(e))
        return None


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

        # Use common HTTP client creation
        client = create_http_client(headers, cache_config=cache_config, timeout=30.0)

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
        # HTTP and key errors are caught and return empty list
        # This ensures graceful degradation
        logger.error("wakatime_fetch_failed", error=str(e), exc_info=True)

    return activities


def _get_wakatime_token(config: dict[str, Any]) -> str | None:
    """
    Retrieve Wakatime token with the following priority:

    1. Token store (encrypted SQLite)
    2. Config file (config.yaml api_key field)
    3. .wakatime.cfg file (~/.wakatime.cfg)
    4. Environment variable (WAKATIME_API_KEY)

    Returns:
        API key string if found, None otherwise.
    """
    # Priority 1 & 2: Token store and config (via get_source_token)
    # Note: get_source_token checks token store first, then config
    token = get_source_token("wakatime", config, config_key="api_key", env_var=None)
    if token:
        return token

    # Priority 3: .wakatime.cfg file
    token = _read_wakatime_cfg()
    if token:
        return token

    # Priority 4: Environment variable
    return os.environ.get("WAKATIME_API_KEY")
