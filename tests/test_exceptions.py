"""Tests for domain exception hierarchy."""

import httpx

from pkm_tool.exceptions import (
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    PKMError,
    RateLimitError,
    SourceError,
)
from pkm_tool.sources.common import classify_http_error


class TestExceptionHierarchy:
    """Test exception class hierarchy and attributes."""

    def test_pkm_error_is_base(self):
        assert issubclass(SourceError, PKMError)
        assert issubclass(AuthenticationError, SourceError)
        assert issubclass(RateLimitError, SourceError)
        assert issubclass(NetworkError, SourceError)
        assert issubclass(ConfigurationError, PKMError)

    def test_source_error_attributes(self):
        err = SourceError("github", "something broke", retriable=True)
        assert err.source == "github"
        assert err.retriable is True
        assert "[github]" in str(err)

    def test_source_error_default_not_retriable(self):
        err = SourceError("github", "oops")
        assert err.retriable is False

    def test_authentication_error_not_retriable(self):
        err = AuthenticationError("wakatime")
        assert err.source == "wakatime"
        assert err.retriable is False

    def test_authentication_error_custom_message(self):
        err = AuthenticationError("github", "Token expired")
        assert "Token expired" in str(err)

    def test_rate_limit_error_retriable(self):
        err = RateLimitError("github", retry_after=60.0)
        assert err.retriable is True
        assert err.retry_after == 60.0
        assert "60.0s" in str(err)

    def test_rate_limit_error_no_retry_after(self):
        err = RateLimitError("github")
        assert err.retry_after is None
        assert err.retriable is True

    def test_network_error_retriable(self):
        err = NetworkError("whoop")
        assert err.retriable is True
        assert err.source == "whoop"

    def test_configuration_error(self):
        err = ConfigurationError("Missing API key")
        assert isinstance(err, PKMError)
        assert "Missing API key" in str(err)


class TestClassifyHttpError:
    """Test HTTP error classification."""

    def _make_response(self, status_code: int, headers: dict | None = None) -> httpx.Response:
        """Create a mock httpx.Response."""
        return httpx.Response(
            status_code=status_code,
            headers=headers or {},
            request=httpx.Request("GET", "https://api.example.com/test"),
        )

    def test_401_returns_authentication_error(self):
        response = self._make_response(401)
        error = httpx.HTTPStatusError("Unauthorized", request=response.request, response=response)
        result = classify_http_error("github", error)
        assert isinstance(result, AuthenticationError)
        assert result.source == "github"
        assert result.retriable is False

    def test_403_returns_authentication_error(self):
        response = self._make_response(403)
        error = httpx.HTTPStatusError("Forbidden", request=response.request, response=response)
        result = classify_http_error("github", error)
        assert isinstance(result, AuthenticationError)

    def test_429_returns_rate_limit_error(self):
        response = self._make_response(429, headers={"Retry-After": "30"})
        error = httpx.HTTPStatusError(
            "Too Many Requests", request=response.request, response=response
        )
        result = classify_http_error("wakatime", error)
        assert isinstance(result, RateLimitError)
        assert result.retry_after == 30.0
        assert result.retriable is True

    def test_429_without_retry_after(self):
        response = self._make_response(429)
        error = httpx.HTTPStatusError(
            "Too Many Requests", request=response.request, response=response
        )
        result = classify_http_error("wakatime", error)
        assert isinstance(result, RateLimitError)
        assert result.retry_after is None

    def test_500_returns_retriable_source_error(self):
        response = self._make_response(500)
        error = httpx.HTTPStatusError(
            "Internal Server Error", request=response.request, response=response
        )
        result = classify_http_error("whoop", error)
        assert isinstance(result, SourceError)
        assert result.retriable is True

    def test_502_returns_retriable_source_error(self):
        response = self._make_response(502)
        error = httpx.HTTPStatusError("Bad Gateway", request=response.request, response=response)
        result = classify_http_error("atlassian", error)
        assert isinstance(result, SourceError)
        assert result.retriable is True

    def test_503_returns_retriable_source_error(self):
        response = self._make_response(503)
        error = httpx.HTTPStatusError(
            "Service Unavailable", request=response.request, response=response
        )
        result = classify_http_error("google_docs", error)
        assert result.retriable is True

    def test_504_returns_retriable_source_error(self):
        response = self._make_response(504)
        error = httpx.HTTPStatusError(
            "Gateway Timeout", request=response.request, response=response
        )
        result = classify_http_error("whoop", error)
        assert result.retriable is True

    def test_404_returns_non_retriable_source_error(self):
        response = self._make_response(404)
        error = httpx.HTTPStatusError("Not Found", request=response.request, response=response)
        result = classify_http_error("github", error)
        assert isinstance(result, SourceError)
        assert not isinstance(result, AuthenticationError)
        assert result.retriable is False

    def test_connect_error_returns_network_error(self):
        error = httpx.ConnectError("Connection refused")
        result = classify_http_error("wakatime", error)
        assert isinstance(result, NetworkError)
        assert result.retriable is True

    def test_timeout_returns_network_error(self):
        error = httpx.ReadTimeout("Read timed out")
        result = classify_http_error("whoop", error)
        assert isinstance(result, NetworkError)
        assert result.retriable is True

    def test_unknown_error_returns_source_error(self):
        error = ValueError("unexpected")
        result = classify_http_error("github", error)
        assert isinstance(result, SourceError)
        assert result.retriable is False
