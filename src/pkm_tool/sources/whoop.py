"""Whoop integration."""

from datetime import date, datetime
from typing import Any

import httpx
import structlog

from pkm_tool.config import CacheConfig
from pkm_tool.models import WhoopRecovery, WhoopSleep, WhoopWorkout
from pkm_tool.sources.common import create_http_client, get_source_token

logger = structlog.get_logger(__name__)

# Whoop API v2 base URL
WHOOP_API_BASE = "https://api.prod.whoop.com/developer"

# Max pages per endpoint to prevent infinite pagination loops
_MAX_PAGES = 10


def _convert_millis_to_minutes(value: int | None, default: int = 0) -> int:
    """Convert milliseconds to minutes, with a default fallback."""
    return value // 60000 if value else default


def _convert_millis_to_minutes_optional(value: int | None) -> int | None:
    """Convert milliseconds to minutes, preserving None."""
    return value // 60000 if value else None


def _parse_sleep_record(record: dict[str, Any], target_date: date) -> WhoopSleep | None:
    """Parse a single sleep record, return None if invalid or doesn't match target date."""
    # Extract timestamps
    start_str = record.get("start")
    end_str = record.get("end")
    if not start_str or not end_str:
        return None

    start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

    # Filter by end date matching target date
    if end.date() != target_date:
        return None

    # Extract sleep stages and metrics
    score = record.get("score", {})
    stages = score.get("stage_summary", {})

    return WhoopSleep(
        start=start,
        end=end,
        duration_minutes=_convert_millis_to_minutes(score.get("total_in_bed_time_milli", 0)),
        sleep_efficiency=score.get("sleep_efficiency_percentage"),
        light_sleep_minutes=_convert_millis_to_minutes_optional(
            stages.get("light_sleep_duration_milli")
        ),
        deep_sleep_minutes=_convert_millis_to_minutes_optional(
            stages.get("slow_wave_sleep_duration_milli")
        ),
        rem_sleep_minutes=_convert_millis_to_minutes_optional(
            stages.get("rem_sleep_duration_milli")
        ),
        awake_minutes=_convert_millis_to_minutes_optional(stages.get("awake_duration_milli")),
        disturbances=score.get("disturbance_count"),
        sleep_performance=score.get("sleep_performance_percentage"),
    )


def _parse_workout_record(record: dict[str, Any], target_date: date) -> WhoopWorkout | None:
    """Parse a single workout record, return None if invalid or doesn't match target date."""
    # Extract timestamps
    start_str = record.get("start")
    end_str = record.get("end")
    if not start_str or not end_str:
        return None

    start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

    # Filter by start date
    if start.date() != target_date:
        return None

    # Extract workout metrics
    score_data = record.get("score", {})
    kilojoule = score_data.get("kilojoule")

    return WhoopWorkout(
        start=start,
        end=end,
        sport_name=record.get("sport_name", "Unknown"),
        strain=score_data.get("strain", 0.0),
        duration_minutes=_convert_millis_to_minutes(score_data.get("duration_milli", 0)),
        average_heart_rate=score_data.get("average_heart_rate"),
        max_heart_rate=score_data.get("max_heart_rate"),
        calories=kilojoule // 4 if kilojoule else None,  # Convert kJ to rough kcal
    )


def _parse_recovery_record(record: dict[str, Any], target_date: date) -> WhoopRecovery | None:
    """Parse a single recovery record, return None if invalid or doesn't match target date."""
    cycle_date_str = record.get("cycle_date")
    if not cycle_date_str:
        return None

    cycle_date = datetime.fromisoformat(cycle_date_str.replace("Z", "+00:00")).date()
    if cycle_date != target_date:
        return None

    score_data = record.get("score", {})
    return WhoopRecovery(
        recovery_score=score_data.get("recovery_score", 0.0),
        hrv=score_data.get("hrv_rmssd_milli", 0.0),
        resting_heart_rate=score_data.get("resting_heart_rate", 0),
        spo2=score_data.get("spo2_percentage"),
        skin_temp=score_data.get("skin_temp_celsius"),
    )


def fetch_whoop_recovery(
    target_date: date,
    config: dict[str, Any],
    cache_config: CacheConfig | None = None,
) -> WhoopRecovery | None:
    """
    Fetch Whoop recovery data for a given date.

    Args:
        target_date: Date to fetch recovery for
        config: Configuration dictionary with 'access_token'
        cache_config: Optional cache configuration for HTTP response caching

    Returns:
        WhoopRecovery object or None if not found/error
    """
    logger.debug("whoop_recovery_fetch_started", date=str(target_date))
    access_token = _get_whoop_token(config)

    if not access_token:
        logger.warning("whoop_no_token", message="No Whoop access token configured")
        return None

    try:
        headers = {"Authorization": f"Bearer {access_token}"}

        # Use common HTTP client creation
        client = create_http_client(headers, cache_config=cache_config, timeout=30.0)

        with client:
            # Fetch recovery cycles for a date range around target date
            # Whoop API v2: GET /v2/recovery
            # API requires ISO 8601 datetime format (YYYY-MM-DDTHH:MM:SSZ)
            start_str = target_date.strftime("%Y-%m-%dT00:00:00Z")
            end_str = target_date.strftime("%Y-%m-%dT23:59:59Z")

            # Paginate through results (max _MAX_PAGES to prevent infinite loops)
            next_token = None
            for _page_num in range(_MAX_PAGES):
                params: dict[str, str] = {"start": start_str, "end": end_str}
                if next_token:
                    params["nextToken"] = next_token

                response = client.get(
                    f"{WHOOP_API_BASE}/v2/recovery",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                # Parse recovery records using helper function
                records = data.get("records", [])
                for record in records:
                    recovery = _parse_recovery_record(record, target_date)
                    if recovery:
                        logger.info(
                            "whoop_recovery_fetched",
                            recovery_score=recovery.recovery_score,
                        )
                        return recovery

                next_token = data.get("next_token")
                if not next_token:
                    break

        logger.debug("whoop_recovery_not_found", date=str(target_date))

    except (httpx.HTTPError, KeyError, ValueError) as e:
        # HTTP, key, and value errors are caught and return None
        # This ensures graceful degradation
        logger.error("whoop_recovery_fetch_failed", error=str(e), exc_info=True)

    return None


def fetch_whoop_sleep(
    target_date: date,
    config: dict[str, Any],
    cache_config: CacheConfig | None = None,
) -> list[WhoopSleep]:
    """
    Fetch Whoop sleep cycles for a given date.

    Args:
        target_date: Date to fetch sleep for (sleep ending on this date)
        config: Configuration dictionary with 'access_token'
        cache_config: Optional cache configuration for HTTP response caching

    Returns:
        List of WhoopSleep objects
    """
    logger.debug("whoop_sleep_fetch_started", date=str(target_date))
    access_token = _get_whoop_token(config)

    if not access_token:
        logger.warning("whoop_no_token", message="No Whoop access token configured")
        return []

    sleep_cycles: list[WhoopSleep] = []

    try:
        headers = {"Authorization": f"Bearer {access_token}"}

        # Use common HTTP client creation
        client = create_http_client(headers, cache_config=cache_config, timeout=30.0)

        with client:
            # Fetch sleep cycles for date range
            # Whoop API v2: GET /v2/activity/sleep
            start_str = target_date.strftime("%Y-%m-%dT00:00:00Z")
            end_str = target_date.strftime("%Y-%m-%dT23:59:59Z")

            # Paginate through results (max _MAX_PAGES to prevent infinite loops)
            next_token = None
            for _page_num in range(_MAX_PAGES):
                params: dict[str, str] = {"start": start_str, "end": end_str}
                if next_token:
                    params["nextToken"] = next_token

                response = client.get(
                    f"{WHOOP_API_BASE}/v2/activity/sleep",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                # Parse sleep cycles using helper function
                records = data.get("records", [])
                for record in records:
                    sleep_cycle = _parse_sleep_record(record, target_date)
                    if sleep_cycle:
                        sleep_cycles.append(sleep_cycle)

                next_token = data.get("next_token")
                if not next_token:
                    break

        logger.info("whoop_sleep_fetched", cycle_count=len(sleep_cycles))

    except (httpx.HTTPError, KeyError, ValueError) as e:
        # HTTP, key, and value errors are caught and return empty list
        # This ensures graceful degradation
        logger.error("whoop_sleep_fetch_failed", error=str(e), exc_info=True)

    return sleep_cycles


def fetch_whoop_workouts(
    target_date: date,
    config: dict[str, Any],
    cache_config: CacheConfig | None = None,
) -> list[WhoopWorkout]:
    """
    Fetch Whoop workouts for a given date.

    Args:
        target_date: Date to fetch workouts for
        config: Configuration dictionary with 'access_token'
        cache_config: Optional cache configuration for HTTP response caching

    Returns:
        List of WhoopWorkout objects
    """
    logger.debug("whoop_workouts_fetch_started", date=str(target_date))
    access_token = _get_whoop_token(config)

    if not access_token:
        logger.warning("whoop_no_token", message="No Whoop access token configured")
        return []

    workouts: list[WhoopWorkout] = []

    try:
        headers = {"Authorization": f"Bearer {access_token}"}

        # Use common HTTP client creation
        client = create_http_client(headers, cache_config=cache_config, timeout=30.0)

        with client:
            # Fetch workouts for date range
            # Whoop API v2: GET /v2/activity/workout
            start_str = target_date.strftime("%Y-%m-%dT00:00:00Z")
            end_str = target_date.strftime("%Y-%m-%dT23:59:59Z")

            # Paginate through results (max _MAX_PAGES to prevent infinite loops)
            next_token = None
            for _page_num in range(_MAX_PAGES):
                params: dict[str, str] = {"start": start_str, "end": end_str}
                if next_token:
                    params["nextToken"] = next_token

                response = client.get(
                    f"{WHOOP_API_BASE}/v2/activity/workout",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                # Parse workouts using helper function
                records = data.get("records", [])
                for record in records:
                    workout = _parse_workout_record(record, target_date)
                    if workout:
                        workouts.append(workout)

                next_token = data.get("next_token")
                if not next_token:
                    break

        logger.info("whoop_workouts_fetched", workout_count=len(workouts))

    except (httpx.HTTPError, KeyError, ValueError) as e:
        # HTTP, key, and value errors are caught and return empty list
        # This ensures graceful degradation
        logger.error("whoop_workouts_fetch_failed", error=str(e), exc_info=True)

    return workouts


def _get_whoop_token(config: dict[str, Any]) -> str | None:
    """Retrieve Whoop access token from secure store or config/env fallback."""
    return get_source_token(
        "whoop", config, config_key="access_token", env_var="WHOOP_ACCESS_TOKEN"
    )
