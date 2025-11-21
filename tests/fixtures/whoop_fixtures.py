"""Test fixtures for Whoop integration."""

from datetime import datetime

import pytest

from pkm_tool.models import WhoopRecovery, WhoopSleep, WhoopWorkout


@pytest.fixture
def sample_whoop_recovery() -> WhoopRecovery:
    """Sample Whoop recovery data."""
    return WhoopRecovery(
        recovery_score=85.0,
        hrv=65.0,
        resting_heart_rate=48,
        spo2=97.5,
        skin_temp=36.2,
    )


@pytest.fixture
def sample_whoop_recovery_minimal() -> WhoopRecovery:
    """Sample Whoop recovery data with minimal fields."""
    return WhoopRecovery(
        recovery_score=75.0,
        hrv=55.0,
        resting_heart_rate=52,
    )


@pytest.fixture
def sample_whoop_sleep() -> WhoopSleep:
    """Sample Whoop sleep cycle."""
    return WhoopSleep(
        start=datetime(2025, 11, 20, 23, 0, 0),
        end=datetime(2025, 11, 21, 7, 0, 0),
        duration_minutes=480,
        sleep_efficiency=95.0,
        light_sleep_minutes=270,
        deep_sleep_minutes=135,
        rem_sleep_minutes=75,
        awake_minutes=15,
        disturbances=2,
        sleep_performance=98.0,
    )


@pytest.fixture
def sample_whoop_sleep_minimal() -> WhoopSleep:
    """Sample Whoop sleep cycle with minimal fields."""
    return WhoopSleep(
        start=datetime(2025, 11, 20, 22, 30, 0),
        end=datetime(2025, 11, 21, 6, 30, 0),
        duration_minutes=480,
    )


@pytest.fixture
def sample_whoop_workout() -> WhoopWorkout:
    """Sample Whoop workout."""
    return WhoopWorkout(
        start=datetime(2025, 11, 21, 6, 0, 0),
        end=datetime(2025, 11, 21, 6, 45, 0),
        sport_name="Running",
        strain=15.2,
        duration_minutes=45,
        average_heart_rate=145,
        max_heart_rate=165,
        calories=450,
    )


@pytest.fixture
def sample_whoop_workout_minimal() -> WhoopWorkout:
    """Sample Whoop workout with minimal fields."""
    return WhoopWorkout(
        start=datetime(2025, 11, 21, 7, 0, 0),
        end=datetime(2025, 11, 21, 7, 30, 0),
        sport_name="Cycling",
        strain=12.5,
        duration_minutes=30,
    )
