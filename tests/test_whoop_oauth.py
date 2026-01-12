"""Tests for Whoop OAuth provider."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import httpx
import pytest

from pkm_tool.auth.oauth.whoop import (
    DEFAULT_CALLBACK_PORT,
    DEFAULT_SCOPES,
    WHOOP_AUTH_ENDPOINT,
    WHOOP_TOKEN_ENDPOINT,
    WhoopOAuthProvider,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ============================================================================
# Constants Tests
# ============================================================================


@pytest.mark.unit
class TestWhoopConstants:
    """Tests for Whoop OAuth constants."""

    def test_auth_endpoint(self) -> None:
        """Test Whoop auth endpoint URL."""
        assert WHOOP_AUTH_ENDPOINT == "https://api.prod.whoop.com/oauth/oauth2/auth"

    def test_token_endpoint(self) -> None:
        """Test Whoop token endpoint URL."""
        assert WHOOP_TOKEN_ENDPOINT == "https://api.prod.whoop.com/oauth/oauth2/token"

    def test_default_scopes(self) -> None:
        """Test default OAuth scopes."""
        assert "read:recovery" in DEFAULT_SCOPES
        assert "read:sleep" in DEFAULT_SCOPES
        assert "read:workout" in DEFAULT_SCOPES
        assert "offline" in DEFAULT_SCOPES  # Required for refresh token

    def test_default_callback_port(self) -> None:
        """Test default callback port."""
        assert DEFAULT_CALLBACK_PORT == 8642


# ============================================================================
# WhoopOAuthProvider Initialization Tests
# ============================================================================


@pytest.mark.unit
class TestWhoopOAuthProviderInit:
    """Tests for WhoopOAuthProvider initialization."""

    def test_basic_init(self) -> None:
        """Test basic initialization with required params."""
        provider = WhoopOAuthProvider(
            client_id="test-client-id",
            client_secret="test-client-secret",
        )

        assert provider.client_id == "test-client-id"
        assert provider.client_secret == "test-client-secret"
        assert provider.scopes == DEFAULT_SCOPES
        assert provider.callback_port == DEFAULT_CALLBACK_PORT

    def test_custom_scopes(self) -> None:
        """Test initialization with custom scopes."""
        custom_scopes = ["read:recovery", "offline"]
        provider = WhoopOAuthProvider(
            client_id="test-client-id",
            client_secret="test-client-secret",
            scopes=custom_scopes,
        )

        assert provider.scopes == custom_scopes

    def test_custom_port(self) -> None:
        """Test initialization with custom callback port."""
        provider = WhoopOAuthProvider(
            client_id="test-client-id",
            client_secret="test-client-secret",
            callback_port=9999,
        )

        assert provider.callback_port == 9999

    def test_custom_http_client(self) -> None:
        """Test initialization with custom HTTP client."""
        custom_client = httpx.Client(timeout=60.0)
        provider = WhoopOAuthProvider(
            client_id="test-client-id",
            client_secret="test-client-secret",
            http_client=custom_client,
        )

        assert provider._http_client == custom_client


# ============================================================================
# WhoopOAuthProvider._build_auth_url Tests
# ============================================================================


@pytest.mark.unit
class TestBuildAuthUrl:
    """Tests for _build_auth_url method."""

    def test_builds_correct_url(self) -> None:
        """Test auth URL is built correctly."""
        provider = WhoopOAuthProvider(
            client_id="my-client-id",
            client_secret="my-client-secret",
        )

        url = provider._build_auth_url(
            state="test-state",
            redirect_uri="http://localhost:8642/callback",
        )

        assert url.startswith(WHOOP_AUTH_ENDPOINT)
        assert "client_id=my-client-id" in url
        assert "redirect_uri=http" in url
        assert "response_type=code" in url
        assert "state=test-state" in url
        assert "scope=" in url

    def test_url_encodes_scopes(self) -> None:
        """Test scopes are properly URL-encoded."""
        provider = WhoopOAuthProvider(
            client_id="test-id",
            client_secret="test-secret",
            scopes=["read:recovery", "read:sleep"],
        )

        url = provider._build_auth_url(
            state="test-state",
            redirect_uri="http://localhost:8642/callback",
        )

        # URL encoding converts spaces to + or %20
        assert "read%3Arecovery" in url or "read:recovery" in url


# ============================================================================
# WhoopOAuthProvider._parse_token_response Tests
# ============================================================================


@pytest.mark.unit
class TestParseTokenResponse:
    """Tests for _parse_token_response method."""

    def test_parses_full_response(self) -> None:
        """Test parsing complete token response."""
        provider = WhoopOAuthProvider(
            client_id="test-id",
            client_secret="test-secret",
        )

        data = {
            "access_token": "access-123",
            "refresh_token": "refresh-456",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        response = provider._parse_token_response(data)

        assert response.access_token == "access-123"
        assert response.refresh_token == "refresh-456"
        assert response.expires_in == 3600
        assert response.token_type == "Bearer"

    def test_parses_minimal_response(self) -> None:
        """Test parsing minimal token response."""
        provider = WhoopOAuthProvider(
            client_id="test-id",
            client_secret="test-secret",
        )

        data = {
            "access_token": "access-123",
        }

        response = provider._parse_token_response(data)

        assert response.access_token == "access-123"
        assert response.refresh_token is None
        assert response.expires_in is None
        assert response.token_type == "bearer"  # Default


# ============================================================================
# WhoopOAuthProvider.refresh_access_token Tests
# ============================================================================


@pytest.mark.unit
class TestRefreshAccessToken:
    """Tests for refresh_access_token method."""

    def test_successful_refresh(self, mocker: MockerFixture) -> None:
        """Test successful token refresh."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        mock_client = Mock()
        mock_client.post.return_value = mock_response

        provider = WhoopOAuthProvider(
            client_id="test-id",
            client_secret="test-secret",
            http_client=mock_client,
        )

        result = provider.refresh_access_token("old-refresh-token")

        assert result is not None
        assert result.access_token == "new-access-token"
        assert result.refresh_token == "new-refresh-token"

        # Verify the request
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == WHOOP_TOKEN_ENDPOINT
        assert call_args[1]["data"]["grant_type"] == "refresh_token"
        assert call_args[1]["data"]["refresh_token"] == "old-refresh-token"

    def test_refresh_failure_non_200(self, mocker: MockerFixture) -> None:
        """Test token refresh with non-200 response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid refresh token"

        mock_client = Mock()
        mock_client.post.return_value = mock_response

        provider = WhoopOAuthProvider(
            client_id="test-id",
            client_secret="test-secret",
            http_client=mock_client,
        )

        result = provider.refresh_access_token("invalid-refresh-token")

        assert result is None

    def test_refresh_http_error(self, mocker: MockerFixture) -> None:
        """Test token refresh with HTTP error."""
        mock_client = Mock()
        mock_client.post.side_effect = httpx.HTTPError("Connection failed")

        provider = WhoopOAuthProvider(
            client_id="test-id",
            client_secret="test-secret",
            http_client=mock_client,
        )

        result = provider.refresh_access_token("refresh-token")

        assert result is None


# ============================================================================
# WhoopOAuthProvider._exchange_code Tests
# ============================================================================


@pytest.mark.unit
class TestExchangeCode:
    """Tests for _exchange_code method."""

    def test_successful_exchange(self, mocker: MockerFixture) -> None:
        """Test successful code exchange."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        mock_client = Mock()
        mock_client.post.return_value = mock_response

        provider = WhoopOAuthProvider(
            client_id="test-id",
            client_secret="test-secret",
            http_client=mock_client,
        )

        result = provider._exchange_code(
            code="auth-code-123",
            redirect_uri="http://localhost:8642/callback",
        )

        assert result is not None
        assert result.access_token == "access-token"

        # Verify request
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[1]["data"]["grant_type"] == "authorization_code"
        assert call_args[1]["data"]["code"] == "auth-code-123"

    def test_exchange_failure(self, mocker: MockerFixture) -> None:
        """Test code exchange failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid code"

        mock_client = Mock()
        mock_client.post.return_value = mock_response

        provider = WhoopOAuthProvider(
            client_id="test-id",
            client_secret="test-secret",
            http_client=mock_client,
        )

        result = provider._exchange_code(
            code="invalid-code",
            redirect_uri="http://localhost:8642/callback",
        )

        assert result is None

    def test_exchange_http_error(self, mocker: MockerFixture) -> None:
        """Test code exchange with HTTP error."""
        mock_client = Mock()
        mock_client.post.side_effect = httpx.HTTPError("Network error")

        provider = WhoopOAuthProvider(
            client_id="test-id",
            client_secret="test-secret",
            http_client=mock_client,
        )

        result = provider._exchange_code(
            code="auth-code",
            redirect_uri="http://localhost:8642/callback",
        )

        assert result is None
