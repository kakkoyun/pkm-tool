"""Whoop integration."""

import os
from datetime import date, datetime
from typing import Any

import httpx

from pkm_tool.auth import AuthManager
from pkm_tool.models import WhoopRecovery, WhoopSleep, WhoopWorkout

_AUTH_MANAGER = AuthManager()


def fetch_whoop_recovery(target_date: date, config: dict[str, Any]) -> WhoopRecovery | None:
    """
    Fetch Whoop recovery data for a given date.

    Args:
        target_date: Date to fetch recovery for
        config: Configuration dictionary with 'access_token'

    Returns:
        WhoopRecovery object or None if not found/error
    """
    access_token = _get_whoop_token(config)

    if not access_token:
        return None

    try:
        headers = {"Authorization": f"Bearer {access_token}"}

        with httpx.Client(headers=headers, timeout=30.0) as client:
            # Fetch recovery cycles for a date range around target date
            # Whoop API v2: GET /v1/recovery
            start_str = target_date.strftime("%Y-%m-%d")
            end_str = target_date.strftime("%Y-%m-%d")

            response = client.get(
                "https://api.whoop.com/v1/recovery",
                params={"start": start_str, "end": end_str},
            )
            response.raise_for_status()
            data = response.json()

            # Parse recovery data
            records = data.get("records", [])
            for record in records:
                # Filter by date
                cycle_date_str = record.get("cycle_date")
                if not cycle_date_str:
                    continue

                cycle_date = datetime.fromisoformat(cycle_date_str.replace("Z", "+00:00")).date()
                if cycle_date != target_date:
                    continue

                # Extract recovery metrics
                score_data = record.get("score", {})
                recovery = WhoopRecovery(
                    recovery_score=score_data.get("recovery_score", 0.0),
                    hrv=score_data.get("hrv_rmssd_milli", 0.0),
                    resting_heart_rate=score_data.get("resting_heart_rate", 0),
                    spo2=score_data.get("spo2_percentage"),
                    skin_temp=score_data.get("skin_temp_celsius"),
                )
                return recovery

    except (httpx.HTTPError, KeyError, ValueError):
        pass

    return None


def fetch_whoop_sleep(target_date: date, config: dict[str, Any]) -> list[WhoopSleep]:
    """
    Fetch Whoop sleep cycles for a given date.

    Args:
        target_date: Date to fetch sleep for (sleep ending on this date)
        config: Configuration dictionary with 'access_token'

    Returns:
        List of WhoopSleep objects
    """
    access_token = _get_whoop_token(config)

    if not access_token:
        return []

    sleep_cycles = []

    try:
        headers = {"Authorization": f"Bearer {access_token}"}

        with httpx.Client(headers=headers, timeout=30.0) as client:
            # Fetch sleep cycles for date range
            # Whoop API v2: GET /v1/sleep
            start_str = target_date.strftime("%Y-%m-%d")
            end_str = target_date.strftime("%Y-%m-%d")

            response = client.get(
                "https://api.whoop.com/v1/sleep",
                params={"start": start_str, "end": end_str},
            )
            response.raise_for_status()
            data = response.json()

            # Parse sleep cycles
            records = data.get("records", [])
            for record in records:
                # Extract timestamps
                start_str = record.get("start")
                end_str = record.get("end")
                if not start_str or not end_str:
                    continue

                start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

                # Filter by end date matching target date
                if end.date() != target_date:
                    continue

                # Extract sleep stages
                stages = record.get("score", {}).get("stage_summary", {})
                duration_ms = record.get("score", {}).get("total_in_bed_time_milli", 0)

                sleep_cycle = WhoopSleep(
                    start=start,
                    end=end,
                    duration_minutes=duration_ms // 60000,
                    sleep_efficiency=record.get("score", {}).get("sleep_efficiency_percentage"),
                    light_sleep_minutes=(
                        stages.get("light_sleep_duration_milli", 0) // 60000
                        if stages.get("light_sleep_duration_milli")
                        else None
                    ),
                    deep_sleep_minutes=(
                        stages.get("slow_wave_sleep_duration_milli", 0) // 60000
                        if stages.get("slow_wave_sleep_duration_milli")
                        else None
                    ),
                    rem_sleep_minutes=(
                        stages.get("rem_sleep_duration_milli", 0) // 60000
                        if stages.get("rem_sleep_duration_milli")
                        else None
                    ),
                    awake_minutes=(
                        stages.get("awake_duration_milli", 0) // 60000
                        if stages.get("awake_duration_milli")
                        else None
                    ),
                    disturbances=record.get("score", {}).get("disturbance_count"),
                    sleep_performance=record.get("score", {}).get("sleep_performance_percentage"),
                )
                sleep_cycles.append(sleep_cycle)

    except (httpx.HTTPError, KeyError, ValueError):
        pass

    return sleep_cycles


def fetch_whoop_workouts(target_date: date, config: dict[str, Any]) -> list[WhoopWorkout]:
    """
    Fetch Whoop workouts for a given date.

    Args:
        target_date: Date to fetch workouts for
        config: Configuration dictionary with 'access_token'

    Returns:
        List of WhoopWorkout objects
    """
    access_token = _get_whoop_token(config)

    if not access_token:
        return []

    workouts = []

    try:
        headers = {"Authorization": f"Bearer {access_token}"}

        with httpx.Client(headers=headers, timeout=30.0) as client:
            # Fetch workouts for date range
            # Whoop API v2: GET /v1/workout
            start_str = target_date.strftime("%Y-%m-%d")
            end_str = target_date.strftime("%Y-%m-%d")

            response = client.get(
                "https://api.whoop.com/v1/workout",
                params={"start": start_str, "end": end_str},
            )
            response.raise_for_status()
            data = response.json()

            # Parse workouts
            records = data.get("records", [])
            for record in records:
                # Extract timestamps
                start_str = record.get("start")
                end_str = record.get("end")
                if not start_str or not end_str:
                    continue

                start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

                # Filter by start date
                if start.date() != target_date:
                    continue

                # Extract workout metrics
                score_data = record.get("score", {})
                duration_ms = score_data.get("duration_milli", 0)

                workout = WhoopWorkout(
                    start=start,
                    end=end,
                    sport_name=record.get("sport_name", "Unknown"),
                    strain=score_data.get("strain", 0.0),
                    duration_minutes=duration_ms // 60000,
                    average_heart_rate=score_data.get("average_heart_rate"),
                    max_heart_rate=score_data.get("max_heart_rate"),
                    calories=score_data.get("kilojoule", 0) // 4
                    if score_data.get("kilojoule")
                    else None,  # Convert kJ to rough kcal
                )
                workouts.append(workout)

    except (httpx.HTTPError, KeyError, ValueError):
        pass

    return workouts


def _get_whoop_token(config: dict[str, Any]) -> str | None:
    """Retrieve Whoop access token from secure store or config/env fallback."""
    stored = _AUTH_MANAGER.get_token("whoop")
    if stored:
        return stored.token
    return config.get("access_token") or os.environ.get("WHOOP_ACCESS_TOKEN")
