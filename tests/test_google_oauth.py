"""Tests for Google OAuth2 provider."""

from unittest.mock import patch

import httpx
import pytest
import respx

from pkm_tool.auth.oauth.base import DeviceCodeResponse, OAuthTokenResponse
from pkm_tool.auth.oauth.google import (
    GOOGLE_DEVICE_CODE_ENDPOINT,
    GOOGLE_TOKEN_ENDPOINT,
    GoogleOAuthProvider,
)


@pytest.fixture
def google_provider() -> GoogleOAuthProvider:
    """Create a Google OAuth provider for testing."""
    return GoogleOAuthProvider(
        client_id="test_client_id",
        client_secret="test_client_secret",
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )


@pytest.fixture
def device_code_response() -> dict:
    """Mock device code response."""
    return {
        "device_code": "test_device_code",
        "user_code": "ABC-123",
        "verification_url": "https://www.google.com/device",
        "expires_in": 1800,
        "interval": 5,
    }


@pytest.fixture
def token_response() -> dict:
    """Mock token response."""
    return {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }


class TestGoogleOAuthProviderInit:
    """Tests for GoogleOAuthProvider initialization."""

    def test_init_with_all_params(self) -> None:
        """Test initialization with all parameters."""
        provider = GoogleOAuthProvider(
            client_id="test_id",
            client_secret="test_secret",
            scopes=["scope1", "scope2"],
        )

        assert provider.client_id == "test_id"
        assert provider.client_secret == "test_secret"
        assert provider.scopes == ["scope1", "scope2"]

    def test_init_with_defaults(self) -> None:
        """Test initialization with default scopes."""
        provider = GoogleOAuthProvider(client_id="test_id")

        assert provider.client_id == "test_id"
        assert provider.client_secret is None
        assert provider.scopes == ["https://www.googleapis.com/auth/drive.readonly"]

    def test_init_with_custom_http_client(self) -> None:
        """Test initialization with custom HTTP client."""
        custom_client = httpx.Client(timeout=60.0)
        provider = GoogleOAuthProvider(
            client_id="test_id",
            http_client=custom_client,
        )

        assert provider._http_client == custom_client
        custom_client.close()


class TestRefreshAccessToken:
    """Tests for refresh_access_token method."""

    @respx.mock
    def test_refresh_success(
        self, google_provider: GoogleOAuthProvider, token_response: dict
    ) -> None:
        """Test successful token refresh."""
        respx.post(GOOGLE_TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=token_response)
        )

        result = google_provider.refresh_access_token("old_refresh_token")

        assert result is not None
        assert isinstance(result, OAuthTokenResponse)
        assert result.access_token == "test_access_token"
        assert result.refresh_token == "test_refresh_token"
        assert result.expires_in == 3600
        assert result.token_type == "Bearer"

    @respx.mock
    def test_refresh_failure(self, google_provider: GoogleOAuthProvider) -> None:
        """Test token refresh failure."""
        respx.post(GOOGLE_TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(401, json={"error": "invalid_grant"})
        )

        result = google_provider.refresh_access_token("invalid_refresh_token")

        assert result is None

    @respx.mock
    def test_refresh_without_refresh_token_in_response(
        self, google_provider: GoogleOAuthProvider
    ) -> None:
        """Test refresh when response doesn't include new refresh token."""
        token_response_no_refresh = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        respx.post(GOOGLE_TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=token_response_no_refresh)
        )

        result = google_provider.refresh_access_token("refresh_token")

        assert result is not None
        assert result.access_token == "new_access_token"
        assert result.refresh_token is None


class TestStartDeviceFlow:
    """Tests for _start_device_flow method."""

    @respx.mock
    def test_start_device_flow_success(
        self, google_provider: GoogleOAuthProvider, device_code_response: dict
    ) -> None:
        """Test successful device flow start."""
        respx.post(GOOGLE_DEVICE_CODE_ENDPOINT).mock(
            return_value=httpx.Response(200, json=device_code_response)
        )

        result = google_provider._start_device_flow()

        assert result is not None
        assert isinstance(result, DeviceCodeResponse)
        assert result.device_code == "test_device_code"
        assert result.user_code == "ABC-123"
        assert result.verification_uri == "https://www.google.com/device"
        assert result.expires_in == 1800
        assert result.interval == 5

    @respx.mock
    def test_start_device_flow_http_error(self, google_provider: GoogleOAuthProvider) -> None:
        """Test device flow start with HTTP error."""
        respx.post(GOOGLE_DEVICE_CODE_ENDPOINT).mock(
            return_value=httpx.Response(400, json={"error": "invalid_request"})
        )

        result = google_provider._start_device_flow()

        assert result is None

    @respx.mock
    def test_start_device_flow_network_error(self, google_provider: GoogleOAuthProvider) -> None:
        """Test device flow start with network error."""
        respx.post(GOOGLE_DEVICE_CODE_ENDPOINT).mock(
            side_effect=httpx.ConnectError("Network error")
        )

        result = google_provider._start_device_flow()

        assert result is None

    @respx.mock
    def test_start_device_flow_default_interval(self, google_provider: GoogleOAuthProvider) -> None:
        """Test device flow with default interval when not provided."""
        response = {
            "device_code": "test_device_code",
            "user_code": "ABC-123",
            "verification_url": "https://www.google.com/device",
            "expires_in": 1800,
            # interval not included
        }

        respx.post(GOOGLE_DEVICE_CODE_ENDPOINT).mock(
            return_value=httpx.Response(200, json=response)
        )

        result = google_provider._start_device_flow()

        assert result is not None
        assert result.interval == 5  # Default value


class TestPollForToken:
    """Tests for _poll_for_token method."""

    @respx.mock
    def test_poll_success(self, google_provider: GoogleOAuthProvider, token_response: dict) -> None:
        """Test successful token polling."""
        device_code = DeviceCodeResponse(
            user_code="ABC-123",
            device_code="test_device_code",
            verification_uri="https://www.google.com/device",
            expires_in=60,
            interval=0,  # Set to 0 for fast test
        )

        respx.post(GOOGLE_TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=token_response)
        )

        result = google_provider._poll_for_token(device_code)

        assert result is not None
        assert result.access_token == "test_access_token"

    @respx.mock
    def test_poll_authorization_pending(
        self, google_provider: GoogleOAuthProvider, token_response: dict
    ) -> None:
        """Test polling with authorization pending then success."""
        device_code = DeviceCodeResponse(
            user_code="ABC-123",
            device_code="test_device_code",
            verification_uri="https://www.google.com/device",
            expires_in=60,
            interval=0,
        )

        # First request returns pending, second returns success
        respx.post(GOOGLE_TOKEN_ENDPOINT).mock(
            side_effect=[
                httpx.Response(400, json={"error": "authorization_pending"}),
                httpx.Response(200, json=token_response),
            ]
        )

        result = google_provider._poll_for_token(device_code)

        assert result is not None
        assert result.access_token == "test_access_token"

    @respx.mock
    def test_poll_slow_down(
        self, google_provider: GoogleOAuthProvider, token_response: dict
    ) -> None:
        """Test polling with slow_down response."""
        device_code = DeviceCodeResponse(
            user_code="ABC-123",
            device_code="test_device_code",
            verification_uri="https://www.google.com/device",
            expires_in=60,
            interval=0,
        )

        # First request returns slow_down, second returns success
        respx.post(GOOGLE_TOKEN_ENDPOINT).mock(
            side_effect=[
                httpx.Response(400, json={"error": "slow_down"}),
                httpx.Response(200, json=token_response),
            ]
        )

        result = google_provider._poll_for_token(device_code)

        assert result is not None
        # Interval should have been increased by 5
        assert device_code.interval == 5

    @respx.mock
    def test_poll_error(self, google_provider: GoogleOAuthProvider) -> None:
        """Test polling with error response."""
        device_code = DeviceCodeResponse(
            user_code="ABC-123",
            device_code="test_device_code",
            verification_uri="https://www.google.com/device",
            expires_in=60,
            interval=0,
        )

        respx.post(GOOGLE_TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(400, json={"error": "access_denied"})
        )

        result = google_provider._poll_for_token(device_code)

        assert result is None

    def test_poll_timeout(self, google_provider: GoogleOAuthProvider) -> None:
        """Test polling timeout."""
        device_code = DeviceCodeResponse(
            user_code="ABC-123",
            device_code="test_device_code",
            verification_uri="https://www.google.com/device",
            expires_in=-1,  # Already expired
            interval=0,
        )

        result = google_provider._poll_for_token(device_code)

        assert result is None


class TestParseTokenResponse:
    """Tests for _parse_token_response method."""

    def test_parse_full_response(self, google_provider: GoogleOAuthProvider) -> None:
        """Test parsing a complete token response."""
        data = {
            "access_token": "access123",
            "refresh_token": "refresh456",
            "expires_in": 7200,
            "token_type": "Bearer",
        }

        result = google_provider._parse_token_response(data)

        assert result.access_token == "access123"
        assert result.refresh_token == "refresh456"
        assert result.expires_in == 7200
        assert result.token_type == "Bearer"

    def test_parse_minimal_response(self, google_provider: GoogleOAuthProvider) -> None:
        """Test parsing a minimal token response."""
        data = {
            "access_token": "access123",
        }

        result = google_provider._parse_token_response(data)

        assert result.access_token == "access123"
        assert result.refresh_token is None
        assert result.expires_in is None
        assert result.token_type == "bearer"  # Default


class TestObtainTokenInteractive:
    """Tests for obtain_token_interactive method."""

    @respx.mock
    def test_obtain_token_interactive_success(
        self, google_provider: GoogleOAuthProvider, device_code_response: dict, token_response: dict
    ) -> None:
        """Test full interactive token flow."""
        respx.post(GOOGLE_DEVICE_CODE_ENDPOINT).mock(
            return_value=httpx.Response(200, json=device_code_response)
        )
        respx.post(GOOGLE_TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=token_response)
        )

        # Patch print to avoid output during test
        with patch("builtins.print"):
            result = google_provider.obtain_token_interactive()

        assert result is not None
        assert result.access_token == "test_access_token"

    @respx.mock
    def test_obtain_token_interactive_device_flow_failure(
        self, google_provider: GoogleOAuthProvider
    ) -> None:
        """Test interactive flow when device flow fails."""
        respx.post(GOOGLE_DEVICE_CODE_ENDPOINT).mock(
            return_value=httpx.Response(400, json={"error": "invalid_client"})
        )

        result = google_provider.obtain_token_interactive()

        assert result is None
