"""Wakatime API mock fixtures."""

import pytest
import respx
from httpx import Response


@pytest.fixture
def wakatime_api_response_data() -> dict:
    """Sample Wakatime API response data."""
    return {
        "data": [
            {
                "projects": [
                    {"name": "pkm-tool", "total_seconds": 7200},
                    {"name": "awesome-app", "total_seconds": 3600},
                ],
                "languages": [
                    {"name": "Python", "total_seconds": 9000},
                    {"name": "JavaScript", "total_seconds": 1800},
                ],
            }
        ]
    }


@pytest.fixture
def mock_wakatime_api_success(
    respx_mock: respx.MockRouter, wakatime_api_response_data: dict
) -> respx.Route:
    """Mock successful Wakatime API response."""
    route = respx_mock.get("https://wakatime.com/api/v1/users/current/summaries").mock(
        return_value=Response(200, json=wakatime_api_response_data)
    )
    return route


@pytest.fixture
def mock_wakatime_api_unauthorized(respx_mock: respx.MockRouter) -> respx.Route:
    """Mock unauthorized Wakatime API response."""
    route = respx_mock.get("https://wakatime.com/api/v1/users/current/summaries").mock(
        return_value=Response(401, json={"error": "Unauthorized"})
    )
    return route


@pytest.fixture
def mock_wakatime_api_rate_limit(respx_mock: respx.MockRouter) -> respx.Route:
    """Mock rate limit Wakatime API response."""
    route = respx_mock.get("https://wakatime.com/api/v1/users/current/summaries").mock(
        return_value=Response(429, json={"error": "Rate limit exceeded"})
    )
    return route


@pytest.fixture
def mock_wakatime_api_server_error(respx_mock: respx.MockRouter) -> respx.Route:
    """Mock server error Wakatime API response."""
    route = respx_mock.get("https://wakatime.com/api/v1/users/current/summaries").mock(
        return_value=Response(500, json={"error": "Internal server error"})
    )
    return route


@pytest.fixture
def mock_wakatime_api_empty(respx_mock: respx.MockRouter) -> respx.Route:
    """Mock empty Wakatime API response (no data for date)."""
    route = respx_mock.get("https://wakatime.com/api/v1/users/current/summaries").mock(
        return_value=Response(200, json={"data": []})
    )
    return route
