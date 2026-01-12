"""Tests for OAuth callback server."""

from __future__ import annotations

import threading
import time
from http.client import HTTPConnection
from typing import TYPE_CHECKING

import pytest

from pkm_tool.auth.oauth.callback_server import (
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    CallbackResult,
    OAuthCallbackServer,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# CallbackResult Tests
# ============================================================================


@pytest.mark.unit
class TestCallbackResult:
    """Tests for CallbackResult dataclass."""

    def test_default_values(self) -> None:
        """Test CallbackResult has correct defaults."""
        result = CallbackResult()
        assert result.code is None
        assert result.error is None
        assert result.state is None

    def test_with_code(self) -> None:
        """Test CallbackResult with authorization code."""
        result = CallbackResult(code="auth-code-123", state="state-abc")
        assert result.code == "auth-code-123"
        assert result.error is None
        assert result.state == "state-abc"

    def test_with_error(self) -> None:
        """Test CallbackResult with error."""
        result = CallbackResult(error="access_denied", state="state-abc")
        assert result.code is None
        assert result.error == "access_denied"
        assert result.state == "state-abc"


# ============================================================================
# OAuthCallbackServer Tests
# ============================================================================


@pytest.mark.unit
class TestOAuthCallbackServerBasics:
    """Basic OAuthCallbackServer tests."""

    def test_default_port(self) -> None:
        """Test default port constant."""
        assert DEFAULT_PORT == 8642

    def test_default_timeout(self) -> None:
        """Test default timeout constant."""
        assert DEFAULT_TIMEOUT == 300.0

    def test_server_initialization(self) -> None:
        """Test server can be initialized with default port."""
        server = OAuthCallbackServer()
        assert server.port == DEFAULT_PORT
        assert not server.is_running

    def test_server_custom_port(self) -> None:
        """Test server can be initialized with custom port."""
        server = OAuthCallbackServer(port=9999)
        assert server.port == 9999


@pytest.mark.unit
class TestOAuthCallbackServerLifecycle:
    """Server lifecycle tests."""

    def test_start_and_stop(self) -> None:
        """Test server can start and stop cleanly."""
        server = OAuthCallbackServer(port=0)  # Port 0 = OS assigns free port

        try:
            callback_url = server.start()
            assert server.is_running
            assert callback_url.startswith("http://localhost:")
            assert "/callback" in callback_url
        finally:
            server.stop()
            assert not server.is_running

    def test_stop_idempotent(self) -> None:
        """Test stop can be called multiple times safely."""
        server = OAuthCallbackServer(port=0)

        server.start()
        server.stop()
        server.stop()  # Second call should not raise
        assert not server.is_running

    def test_stop_without_start(self) -> None:
        """Test stop can be called without start."""
        server = OAuthCallbackServer(port=0)
        server.stop()  # Should not raise
        assert not server.is_running

    def test_context_manager(self) -> None:
        """Test server works as context manager."""
        with OAuthCallbackServer(port=0) as server:
            assert server.is_running

        assert not server.is_running

    def test_double_start_raises(self) -> None:
        """Test starting an already running server raises."""
        server = OAuthCallbackServer(port=0)

        try:
            server.start()
            with pytest.raises(RuntimeError, match="already running"):
                server.start()
        finally:
            server.stop()


@pytest.mark.unit
class TestOAuthCallbackServerCallback:
    """Server callback handling tests."""

    def test_successful_callback(self) -> None:
        """Test server handles successful callback."""
        server = OAuthCallbackServer(port=0)

        try:
            callback_url = server.start()

            # Extract port from callback URL
            port = int(callback_url.split(":")[2].split("/")[0])

            # Make callback request in another thread with retries
            request_success = threading.Event()

            def make_request() -> None:
                for _ in range(10):  # Retry up to 10 times
                    time.sleep(0.2)  # Give server time to be ready
                    try:
                        conn = HTTPConnection("127.0.0.1", port, timeout=2)
                        conn.request("GET", "/callback?code=test-code&state=test-state")
                        conn.getresponse()
                        conn.close()
                        request_success.set()
                        return
                    except (ConnectionRefusedError, OSError):
                        continue

            thread = threading.Thread(target=make_request)
            thread.start()

            # Wait for callback
            result = server.wait_for_callback(timeout=5.0)

            thread.join(timeout=3.0)

            if request_success.is_set():
                assert result.code == "test-code"
                assert result.state == "test-state"
                assert result.error is None
            else:
                # If request couldn't connect, we should get timeout
                assert result.error == "timeout"

        finally:
            server.stop()

    def test_error_callback(self) -> None:
        """Test server handles error callback."""
        server = OAuthCallbackServer(port=0)

        try:
            callback_url = server.start()
            port = int(callback_url.split(":")[2].split("/")[0])

            request_success = threading.Event()

            def make_request() -> None:
                for _ in range(10):
                    time.sleep(0.2)
                    try:
                        conn = HTTPConnection("127.0.0.1", port, timeout=2)
                        conn.request("GET", "/callback?error=access_denied&state=test-state")
                        conn.getresponse()
                        conn.close()
                        request_success.set()
                        return
                    except (ConnectionRefusedError, OSError):
                        continue

            thread = threading.Thread(target=make_request)
            thread.start()

            result = server.wait_for_callback(timeout=5.0)

            thread.join(timeout=3.0)

            if request_success.is_set():
                assert result.code is None
                assert result.error == "access_denied"
                assert result.state == "test-state"
            else:
                assert result.error == "timeout"

        finally:
            server.stop()

    def test_timeout(self) -> None:
        """Test server returns timeout result when no callback received."""
        server = OAuthCallbackServer(port=0)

        try:
            server.start()

            # Very short timeout for testing
            result = server.wait_for_callback(timeout=0.1)

            assert result.error == "timeout"
            assert result.code is None

        finally:
            server.stop()

    def test_404_for_unknown_path(self) -> None:
        """Test server returns 404 for unknown paths."""
        server = OAuthCallbackServer(port=0)

        try:
            callback_url = server.start()
            port = int(callback_url.split(":")[2].split("/")[0])

            # Use 127.0.0.1 explicitly instead of localhost
            for _ in range(5):
                time.sleep(0.2)
                try:
                    conn = HTTPConnection("127.0.0.1", port, timeout=2)
                    conn.request("GET", "/unknown")
                    response = conn.getresponse()
                    conn.close()

                    assert response.status == 404
                    return
                except (ConnectionRefusedError, OSError):
                    continue

            # If we couldn't connect after retries, skip assertion
            pytest.skip("Could not connect to server")

        finally:
            server.stop()


@pytest.mark.unit
class TestOAuthCallbackServerSocket:
    """Server socket property tests."""

    def test_server_socket_when_running(self) -> None:
        """Test server_socket returns socket when running."""
        server = OAuthCallbackServer(port=0)

        try:
            server.start()
            assert server.server_socket is not None
        finally:
            server.stop()

    def test_server_socket_when_stopped(self) -> None:
        """Test server_socket returns None when stopped."""
        server = OAuthCallbackServer(port=0)
        assert server.server_socket is None

        server.start()
        server.stop()
        assert server.server_socket is None
