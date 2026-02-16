"""Contract tests verifying all sources conform to the source interface.

Every HTTP source must:
1. Accept (target_date, config) or (target_date, config, cache_config) signature
2. Return empty list/None when token is missing
3. Return empty list/None on HTTP 401 (authentication failure)
4. Return empty list/None on HTTP 500 (server error)
5. Never raise exceptions to the caller
"""

from datetime import date
from unittest.mock import patch

import httpx
import pytest
import respx

from pkm_tool.sources.github import fetch_github_activities
from pkm_tool.sources.google_docs import fetch_google_docs
from pkm_tool.sources.wakatime import fetch_wakatime_activities
from pkm_tool.sources.whoop import (
    fetch_whoop_recovery,
    fetch_whoop_sleep,
    fetch_whoop_workouts,
)

TARGET_DATE = date(2025, 11, 21)
# Config with all token variants so any source can find a token
ALL_TOKENS_CONFIG = {"token": "test", "access_token": "test", "api_key": "test"}


# Sources returning list (should return [])
LIST_SOURCES = [
    pytest.param(fetch_github_activities, id="github"),
    pytest.param(fetch_google_docs, id="google_docs"),
    pytest.param(fetch_wakatime_activities, id="wakatime"),
    pytest.param(fetch_whoop_sleep, id="whoop_sleep"),
    pytest.param(fetch_whoop_workouts, id="whoop_workouts"),
]

# Sources returning optional single object (should return None)
OPTIONAL_SOURCES = [
    pytest.param(fetch_whoop_recovery, id="whoop_recovery"),
]


class TestMissingTokenReturnsEmpty:
    """All sources must return empty results when no token is available."""

    @pytest.mark.parametrize("fetch_func", LIST_SOURCES)
    def test_list_source_empty_on_missing_token(self, fetch_func) -> None:
        with patch("pkm_tool.sources.common.AuthManager") as mock_cls:
            mock_cls.return_value.get_token.return_value = None
            result = fetch_func(TARGET_DATE, {})
        assert result == []

    @pytest.mark.parametrize("fetch_func", OPTIONAL_SOURCES)
    def test_optional_source_none_on_missing_token(self, fetch_func) -> None:
        with patch("pkm_tool.sources.common.AuthManager") as mock_cls:
            mock_cls.return_value.get_token.return_value = None
            result = fetch_func(TARGET_DATE, {})
        assert result is None


class TestHttpErrorReturnsEmpty:
    """All sources must return empty results on HTTP errors."""

    @respx.mock
    @pytest.mark.parametrize("fetch_func", LIST_SOURCES)
    def test_list_source_empty_on_500(self, fetch_func) -> None:
        """Server errors return empty list, never raise."""
        # Catch all requests and return 500
        respx.route().mock(
            return_value=httpx.Response(500, json={"error": "Internal Server Error"})
        )
        result = fetch_func(TARGET_DATE, ALL_TOKENS_CONFIG)
        assert result == []

    @respx.mock
    @pytest.mark.parametrize("fetch_func", OPTIONAL_SOURCES)
    def test_optional_source_none_on_500(self, fetch_func) -> None:
        """Server errors return None, never raise."""
        respx.route().mock(
            return_value=httpx.Response(500, json={"error": "Internal Server Error"})
        )
        result = fetch_func(TARGET_DATE, ALL_TOKENS_CONFIG)
        assert result is None

    @respx.mock
    @pytest.mark.parametrize("fetch_func", LIST_SOURCES)
    def test_list_source_empty_on_401(self, fetch_func) -> None:
        """Auth errors return empty list, never raise."""
        respx.route().mock(return_value=httpx.Response(401, json={"error": "Unauthorized"}))
        result = fetch_func(TARGET_DATE, ALL_TOKENS_CONFIG)
        assert result == []

    @respx.mock
    @pytest.mark.parametrize("fetch_func", OPTIONAL_SOURCES)
    def test_optional_source_none_on_401(self, fetch_func) -> None:
        """Auth errors return None, never raise."""
        respx.route().mock(return_value=httpx.Response(401, json={"error": "Unauthorized"}))
        result = fetch_func(TARGET_DATE, ALL_TOKENS_CONFIG)
        assert result is None


class TestConnectionErrorReturnsEmpty:
    """All sources must handle connection errors gracefully."""

    @respx.mock
    @pytest.mark.parametrize("fetch_func", LIST_SOURCES)
    def test_list_source_empty_on_connect_error(self, fetch_func) -> None:
        """Connection errors return empty list."""
        respx.route().mock(side_effect=httpx.ConnectError("Connection refused"))
        result = fetch_func(TARGET_DATE, ALL_TOKENS_CONFIG)
        assert result == []

    @respx.mock
    @pytest.mark.parametrize("fetch_func", OPTIONAL_SOURCES)
    def test_optional_source_none_on_connect_error(self, fetch_func) -> None:
        """Connection errors return None."""
        respx.route().mock(side_effect=httpx.ConnectError("Connection refused"))
        result = fetch_func(TARGET_DATE, ALL_TOKENS_CONFIG)
        assert result is None
