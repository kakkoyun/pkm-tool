"""Tests for retry transport with exponential backoff."""

from unittest.mock import patch

import httpx
import pytest

from pkm_tool.retry import RetryTransport


class TestRetryTransport:
    """Test RetryTransport behavior."""

    def _make_transport(self, responses: list[httpx.Response]) -> httpx.MockTransport:
        """Create a mock transport that returns responses in sequence."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            idx = min(call_count, len(responses) - 1)
            call_count += 1
            return responses[idx]

        return httpx.MockTransport(handler)

    def test_successful_request_no_retry(self):
        """Successful request should not trigger retry."""
        mock = self._make_transport([httpx.Response(200)])
        transport = RetryTransport(transport=mock, max_retries=3, base_delay=0.01)

        response = transport.handle_request(httpx.Request("GET", "https://api.example.com"))
        assert response.status_code == 200

    @pytest.mark.parametrize("status_code", [500, 502, 503, 504])
    def test_retry_on_server_error(self, status_code: int):
        """Server errors should trigger retry."""
        mock = self._make_transport(
            [
                httpx.Response(status_code),
                httpx.Response(200),
            ]
        )
        transport = RetryTransport(transport=mock, max_retries=3, base_delay=0.01)

        with patch("pkm_tool.retry.time.sleep"):
            response = transport.handle_request(httpx.Request("GET", "https://api.example.com"))
        assert response.status_code == 200

    def test_retry_on_429_with_retry_after(self):
        """429 should retry and respect Retry-After header."""
        mock = self._make_transport(
            [
                httpx.Response(429, headers={"Retry-After": "2"}),
                httpx.Response(200),
            ]
        )
        transport = RetryTransport(transport=mock, max_retries=3, base_delay=0.01)

        with patch("pkm_tool.retry.time.sleep") as mock_sleep:
            response = transport.handle_request(httpx.Request("GET", "https://api.example.com"))
        assert response.status_code == 200
        # Should have respected the Retry-After header
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] == 2.0

    def test_no_retry_on_401(self):
        """401 should not trigger retry."""
        mock = self._make_transport([httpx.Response(401)])
        transport = RetryTransport(transport=mock, max_retries=3, base_delay=0.01)

        response = transport.handle_request(httpx.Request("GET", "https://api.example.com"))
        assert response.status_code == 401

    def test_no_retry_on_404(self):
        """404 should not trigger retry."""
        mock = self._make_transport([httpx.Response(404)])
        transport = RetryTransport(transport=mock, max_retries=3, base_delay=0.01)

        response = transport.handle_request(httpx.Request("GET", "https://api.example.com"))
        assert response.status_code == 404

    def test_max_retries_exhausted_returns_last_response(self):
        """After exhausting retries, should return the last error response."""
        mock = self._make_transport(
            [
                httpx.Response(500),
                httpx.Response(500),
                httpx.Response(500),
                httpx.Response(500),
            ]
        )
        transport = RetryTransport(transport=mock, max_retries=3, base_delay=0.01)

        with patch("pkm_tool.retry.time.sleep"):
            response = transport.handle_request(httpx.Request("GET", "https://api.example.com"))
        assert response.status_code == 500

    def test_retry_on_connect_error(self):
        """Connection errors should trigger retry."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise httpx.ConnectError("Connection refused")
            return httpx.Response(200)

        mock = httpx.MockTransport(handler)
        transport = RetryTransport(transport=mock, max_retries=3, base_delay=0.01)

        with patch("pkm_tool.retry.time.sleep"):
            response = transport.handle_request(httpx.Request("GET", "https://api.example.com"))
        assert response.status_code == 200

    def test_retry_on_timeout(self):
        """Timeout errors should trigger retry."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise httpx.ReadTimeout("Read timed out")
            return httpx.Response(200)

        mock = httpx.MockTransport(handler)
        transport = RetryTransport(transport=mock, max_retries=3, base_delay=0.01)

        with patch("pkm_tool.retry.time.sleep"):
            response = transport.handle_request(httpx.Request("GET", "https://api.example.com"))
        assert response.status_code == 200

    def test_connect_error_exhausted_raises(self):
        """After exhausting retries on connect errors, should raise."""

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        mock = httpx.MockTransport(handler)
        transport = RetryTransport(transport=mock, max_retries=2, base_delay=0.01)

        with patch("pkm_tool.retry.time.sleep"):
            with pytest.raises(httpx.ConnectError):
                transport.handle_request(httpx.Request("GET", "https://api.example.com"))

    def test_exponential_backoff_timing(self):
        """Verify delays increase exponentially."""
        mock = self._make_transport(
            [
                httpx.Response(500),
                httpx.Response(500),
                httpx.Response(500),
                httpx.Response(200),
            ]
        )
        transport = RetryTransport(transport=mock, max_retries=3, base_delay=1.0, max_delay=30.0)

        with (
            patch("pkm_tool.retry.time.sleep") as mock_sleep,
            patch("pkm_tool.retry.random.uniform", return_value=0.0),
        ):
            transport.handle_request(httpx.Request("GET", "https://api.example.com"))

        # Should have 3 sleep calls with exponential delays: 1, 2, 4
        assert mock_sleep.call_count == 3
        delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0
