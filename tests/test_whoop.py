"""Tests for Whoop integration."""

from datetime import date
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from pkm_tool.config import CacheConfig
from pkm_tool.models import WhoopRecovery, WhoopSleep, WhoopWorkout
from pkm_tool.sources.whoop import (
    _get_whoop_token,
    fetch_whoop_recovery,
    fetch_whoop_sleep,
    fetch_whoop_workouts,
)


@pytest.fixture
def whoop_config() -> dict[str, str]:
    """Sample Whoop configuration with access token."""
    return {"access_token": "test_whoop_token"}


@pytest.fixture
def whoop_recovery_response() -> dict:
    """Mock Whoop recovery API response."""
    return {
        "records": [
            {
                "cycle_date": "2025-11-21T00:00:00Z",
                "score": {
                    "recovery_score": 85.0,
                    "hrv_rmssd_milli": 65.0,
                    "resting_heart_rate": 48,
                    "spo2_percentage": 97.5,
                    "skin_temp_celsius": 36.2,
                },
            }
        ]
    }


@pytest.fixture
def whoop_sleep_response() -> dict:
    """Mock Whoop sleep API response."""
    return {
        "records": [
            {
                "start": "2025-11-20T23:00:00Z",
                "end": "2025-11-21T07:00:00Z",
                "score": {
                    "total_in_bed_time_milli": 28800000,  # 480 minutes
                    "sleep_efficiency_percentage": 95.0,
                    "stage_summary": {
                        "light_sleep_duration_milli": 16200000,  # 270 minutes
                        "slow_wave_sleep_duration_milli": 8100000,  # 135 minutes
                        "rem_sleep_duration_milli": 4500000,  # 75 minutes
                        "awake_duration_milli": 900000,  # 15 minutes
                    },
                    "disturbance_count": 2,
                    "sleep_performance_percentage": 98.0,
                },
            }
        ]
    }


@pytest.fixture
def whoop_workouts_response() -> dict:
    """Mock Whoop workouts API response."""
    return {
        "records": [
            {
                "start": "2025-11-21T06:00:00Z",
                "end": "2025-11-21T06:45:00Z",
                "sport_name": "Running",
                "score": {
                    "strain": 15.2,
                    "duration_milli": 2700000,  # 45 minutes
                    "average_heart_rate": 145,
                    "max_heart_rate": 165,
                    "kilojoule": 1800,  # ~450 kcal
                },
            }
        ]
    }


class TestFetchWhoopRecovery:
    """Tests for fetch_whoop_recovery function."""

    @respx.mock
    def test_fetch_recovery_success(
        self, whoop_config: dict[str, str], whoop_recovery_response: dict
    ) -> None:
        """Test successful recovery data fetch."""
        target_date = date(2025, 11, 21)

        respx.get("https://api.whoop.com/v1/recovery").mock(
            return_value=httpx.Response(200, json=whoop_recovery_response)
        )

        result = fetch_whoop_recovery(target_date, whoop_config)

        assert result is not None
        assert isinstance(result, WhoopRecovery)
        assert result.recovery_score == 85.0
        assert result.hrv == 65.0
        assert result.resting_heart_rate == 48
        assert result.spo2 == 97.5
        assert result.skin_temp == 36.2

    @respx.mock
    def test_fetch_recovery_no_token(self) -> None:
        """Test recovery fetch with no access token."""
        target_date = date(2025, 11, 21)
        config: dict = {}

        result = fetch_whoop_recovery(target_date, config)

        assert result is None

    @respx.mock
    def test_fetch_recovery_empty_response(self, whoop_config: dict[str, str]) -> None:
        """Test recovery fetch with empty response."""
        target_date = date(2025, 11, 21)

        respx.get("https://api.whoop.com/v1/recovery").mock(
            return_value=httpx.Response(200, json={"records": []})
        )

        result = fetch_whoop_recovery(target_date, whoop_config)

        assert result is None

    @respx.mock
    def test_fetch_recovery_http_error(self, whoop_config: dict[str, str]) -> None:
        """Test recovery fetch with HTTP error."""
        target_date = date(2025, 11, 21)

        respx.get("https://api.whoop.com/v1/recovery").mock(
            return_value=httpx.Response(500, json={"error": "Server error"})
        )

        result = fetch_whoop_recovery(target_date, whoop_config)

        assert result is None

    @respx.mock
    def test_fetch_recovery_date_mismatch(self, whoop_config: dict[str, str]) -> None:
        """Test recovery fetch when returned date doesn't match target date."""
        target_date = date(2025, 11, 21)
        response = {
            "records": [
                {
                    "cycle_date": "2025-11-20T00:00:00Z",  # Different date
                    "score": {
                        "recovery_score": 85.0,
                        "hrv_rmssd_milli": 65.0,
                        "resting_heart_rate": 48,
                    },
                }
            ]
        }

        respx.get("https://api.whoop.com/v1/recovery").mock(
            return_value=httpx.Response(200, json=response)
        )

        result = fetch_whoop_recovery(target_date, whoop_config)

        assert result is None

    @respx.mock
    def test_fetch_recovery_missing_cycle_date(self, whoop_config: dict[str, str]) -> None:
        """Test recovery fetch when cycle_date is missing."""
        target_date = date(2025, 11, 21)
        response = {
            "records": [
                {
                    "score": {
                        "recovery_score": 85.0,
                        "hrv_rmssd_milli": 65.0,
                        "resting_heart_rate": 48,
                    },
                }
            ]
        }

        respx.get("https://api.whoop.com/v1/recovery").mock(
            return_value=httpx.Response(200, json=response)
        )

        result = fetch_whoop_recovery(target_date, whoop_config)

        assert result is None


class TestFetchWhoopSleep:
    """Tests for fetch_whoop_sleep function."""

    @respx.mock
    def test_fetch_sleep_success(
        self, whoop_config: dict[str, str], whoop_sleep_response: dict
    ) -> None:
        """Test successful sleep data fetch."""
        target_date = date(2025, 11, 21)

        respx.get("https://api.whoop.com/v1/sleep").mock(
            return_value=httpx.Response(200, json=whoop_sleep_response)
        )

        result = fetch_whoop_sleep(target_date, whoop_config)

        assert len(result) == 1
        sleep = result[0]
        assert isinstance(sleep, WhoopSleep)
        assert sleep.duration_minutes == 480
        assert sleep.sleep_efficiency == 95.0
        assert sleep.light_sleep_minutes == 270
        assert sleep.deep_sleep_minutes == 135
        assert sleep.rem_sleep_minutes == 75
        assert sleep.awake_minutes == 15
        assert sleep.disturbances == 2
        assert sleep.sleep_performance == 98.0

    @respx.mock
    def test_fetch_sleep_no_token(self) -> None:
        """Test sleep fetch with no access token."""
        target_date = date(2025, 11, 21)
        config: dict = {}

        result = fetch_whoop_sleep(target_date, config)

        assert result == []

    @respx.mock
    def test_fetch_sleep_empty_response(self, whoop_config: dict[str, str]) -> None:
        """Test sleep fetch with empty response."""
        target_date = date(2025, 11, 21)

        respx.get("https://api.whoop.com/v1/sleep").mock(
            return_value=httpx.Response(200, json={"records": []})
        )

        result = fetch_whoop_sleep(target_date, whoop_config)

        assert result == []

    @respx.mock
    def test_fetch_sleep_http_error(self, whoop_config: dict[str, str]) -> None:
        """Test sleep fetch with HTTP error."""
        target_date = date(2025, 11, 21)

        respx.get("https://api.whoop.com/v1/sleep").mock(
            return_value=httpx.Response(500, json={"error": "Server error"})
        )

        result = fetch_whoop_sleep(target_date, whoop_config)

        assert result == []

    @respx.mock
    def test_fetch_sleep_date_mismatch(self, whoop_config: dict[str, str]) -> None:
        """Test sleep fetch when end date doesn't match target date."""
        target_date = date(2025, 11, 21)
        response = {
            "records": [
                {
                    "start": "2025-11-19T23:00:00Z",
                    "end": "2025-11-20T07:00:00Z",  # Different end date
                    "score": {
                        "total_in_bed_time_milli": 28800000,
                    },
                }
            ]
        }

        respx.get("https://api.whoop.com/v1/sleep").mock(
            return_value=httpx.Response(200, json=response)
        )

        result = fetch_whoop_sleep(target_date, whoop_config)

        assert result == []

    @respx.mock
    def test_fetch_sleep_missing_timestamps(self, whoop_config: dict[str, str]) -> None:
        """Test sleep fetch with missing timestamps."""
        target_date = date(2025, 11, 21)
        response = {
            "records": [
                {
                    "score": {
                        "total_in_bed_time_milli": 28800000,
                    },
                }
            ]
        }

        respx.get("https://api.whoop.com/v1/sleep").mock(
            return_value=httpx.Response(200, json=response)
        )

        result = fetch_whoop_sleep(target_date, whoop_config)

        assert result == []


class TestFetchWhoopWorkouts:
    """Tests for fetch_whoop_workouts function."""

    @respx.mock
    def test_fetch_workouts_success(
        self, whoop_config: dict[str, str], whoop_workouts_response: dict
    ) -> None:
        """Test successful workouts data fetch."""
        target_date = date(2025, 11, 21)

        respx.get("https://api.whoop.com/v1/workout").mock(
            return_value=httpx.Response(200, json=whoop_workouts_response)
        )

        result = fetch_whoop_workouts(target_date, whoop_config)

        assert len(result) == 1
        workout = result[0]
        assert isinstance(workout, WhoopWorkout)
        assert workout.sport_name == "Running"
        assert workout.strain == 15.2
        assert workout.duration_minutes == 45
        assert workout.average_heart_rate == 145
        assert workout.max_heart_rate == 165
        assert workout.calories == 450

    @respx.mock
    def test_fetch_workouts_no_token(self) -> None:
        """Test workouts fetch with no access token."""
        target_date = date(2025, 11, 21)
        config: dict = {}

        result = fetch_whoop_workouts(target_date, config)

        assert result == []

    @respx.mock
    def test_fetch_workouts_empty_response(self, whoop_config: dict[str, str]) -> None:
        """Test workouts fetch with empty response."""
        target_date = date(2025, 11, 21)

        respx.get("https://api.whoop.com/v1/workout").mock(
            return_value=httpx.Response(200, json={"records": []})
        )

        result = fetch_whoop_workouts(target_date, whoop_config)

        assert result == []

    @respx.mock
    def test_fetch_workouts_http_error(self, whoop_config: dict[str, str]) -> None:
        """Test workouts fetch with HTTP error."""
        target_date = date(2025, 11, 21)

        respx.get("https://api.whoop.com/v1/workout").mock(
            return_value=httpx.Response(500, json={"error": "Server error"})
        )

        result = fetch_whoop_workouts(target_date, whoop_config)

        assert result == []

    @respx.mock
    def test_fetch_workouts_date_mismatch(self, whoop_config: dict[str, str]) -> None:
        """Test workouts fetch when start date doesn't match target date."""
        target_date = date(2025, 11, 21)
        response = {
            "records": [
                {
                    "start": "2025-11-20T06:00:00Z",  # Different start date
                    "end": "2025-11-20T06:45:00Z",
                    "sport_name": "Running",
                    "score": {
                        "strain": 15.2,
                        "duration_milli": 2700000,
                    },
                }
            ]
        }

        respx.get("https://api.whoop.com/v1/workout").mock(
            return_value=httpx.Response(200, json=response)
        )

        result = fetch_whoop_workouts(target_date, whoop_config)

        assert result == []

    @respx.mock
    def test_fetch_workouts_missing_timestamps(self, whoop_config: dict[str, str]) -> None:
        """Test workouts fetch with missing timestamps."""
        target_date = date(2025, 11, 21)
        response = {
            "records": [
                {
                    "sport_name": "Running",
                    "score": {
                        "strain": 15.2,
                        "duration_milli": 2700000,
                    },
                }
            ]
        }

        respx.get("https://api.whoop.com/v1/workout").mock(
            return_value=httpx.Response(200, json=response)
        )

        result = fetch_whoop_workouts(target_date, whoop_config)

        assert result == []

    @respx.mock
    def test_fetch_workouts_multiple(self, whoop_config: dict[str, str]) -> None:
        """Test fetching multiple workouts."""
        target_date = date(2025, 11, 21)
        response = {
            "records": [
                {
                    "start": "2025-11-21T06:00:00Z",
                    "end": "2025-11-21T06:45:00Z",
                    "sport_name": "Running",
                    "score": {"strain": 15.2, "duration_milli": 2700000},
                },
                {
                    "start": "2025-11-21T18:00:00Z",
                    "end": "2025-11-21T18:30:00Z",
                    "sport_name": "Cycling",
                    "score": {"strain": 10.5, "duration_milli": 1800000},
                },
            ]
        }

        respx.get("https://api.whoop.com/v1/workout").mock(
            return_value=httpx.Response(200, json=response)
        )

        result = fetch_whoop_workouts(target_date, whoop_config)

        assert len(result) == 2
        assert result[0].sport_name == "Running"
        assert result[1].sport_name == "Cycling"


class TestGetWhoopToken:
    """Tests for _get_whoop_token helper function."""

    def test_get_token_from_config(self) -> None:
        """Test getting token from config."""
        config = {"access_token": "config_token"}

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None
            mock_auth_class.return_value = mock_auth

            result = _get_whoop_token(config)

        assert result == "config_token"

    def test_get_token_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting token from environment variable."""
        monkeypatch.setenv("WHOOP_ACCESS_TOKEN", "env_token")

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None
            mock_auth_class.return_value = mock_auth

            result = _get_whoop_token({})

        assert result == "env_token"

    def test_get_token_from_stored(self) -> None:
        """Test getting token from stored credentials."""
        mock_token = MagicMock()
        mock_token.token = "stored_token"

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = mock_token
            mock_auth_class.return_value = mock_auth

            result = _get_whoop_token({})

        assert result == "stored_token"

    def test_get_token_priority(self) -> None:
        """Test that stored token has priority over config."""
        mock_token = MagicMock()
        mock_token.token = "stored_token"
        config = {"access_token": "config_token"}

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = mock_token
            mock_auth_class.return_value = mock_auth

            result = _get_whoop_token(config)

        # Stored token should take priority
        assert result == "stored_token"


class TestWhoopWithCache:
    """Tests for Whoop functions with cache enabled."""

    @respx.mock
    def test_fetch_recovery_with_cache(
        self, whoop_config: dict[str, str], whoop_recovery_response: dict, tmp_path
    ) -> None:
        """Test recovery fetch with caching enabled."""
        target_date = date(2025, 11, 21)
        cache_config = CacheConfig(
            enabled=True,
            directory=str(tmp_path / "cache"),
            ttl_hours=24,
        )

        respx.get("https://api.whoop.com/v1/recovery").mock(
            return_value=httpx.Response(200, json=whoop_recovery_response)
        )

        result = fetch_whoop_recovery(target_date, whoop_config, cache_config)

        assert result is not None
        assert result.recovery_score == 85.0

    @respx.mock
    def test_fetch_sleep_with_cache(
        self, whoop_config: dict[str, str], whoop_sleep_response: dict, tmp_path
    ) -> None:
        """Test sleep fetch with caching enabled."""
        target_date = date(2025, 11, 21)
        cache_config = CacheConfig(
            enabled=True,
            directory=str(tmp_path / "cache"),
            ttl_hours=24,
        )

        respx.get("https://api.whoop.com/v1/sleep").mock(
            return_value=httpx.Response(200, json=whoop_sleep_response)
        )

        result = fetch_whoop_sleep(target_date, whoop_config, cache_config)

        assert len(result) == 1

    @respx.mock
    def test_fetch_workouts_with_cache(
        self, whoop_config: dict[str, str], whoop_workouts_response: dict, tmp_path
    ) -> None:
        """Test workouts fetch with caching enabled."""
        target_date = date(2025, 11, 21)
        cache_config = CacheConfig(
            enabled=True,
            directory=str(tmp_path / "cache"),
            ttl_hours=24,
        )

        respx.get("https://api.whoop.com/v1/workout").mock(
            return_value=httpx.Response(200, json=whoop_workouts_response)
        )

        result = fetch_whoop_workouts(target_date, whoop_config, cache_config)

        assert len(result) == 1
