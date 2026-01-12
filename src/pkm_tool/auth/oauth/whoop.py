"""Whoop OAuth2 provider using authorization code flow.

Whoop uses the standard OAuth2 Authorization Code flow, which requires:
1. Opening a browser for user authentication
2. Receiving the authorization code via a local callback server
3. Exchanging the code for access and refresh tokens

Reference: https://developer.whoop.com/docs/developing/oauth/
"""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog

from pkm_tool.auth.browser import open_browser
from pkm_tool.auth.oauth.base import OAuthTokenResponse
from pkm_tool.auth.oauth.callback_server import OAuthCallbackServer

logger = structlog.get_logger(__name__)

# Whoop OAuth2 endpoints
WHOOP_AUTH_ENDPOINT = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_ENDPOINT = "https://api.prod.whoop.com/oauth/oauth2/token"

# Default OAuth scopes for Whoop
# offline scope is required to get a refresh token
DEFAULT_SCOPES = ["read:recovery", "read:sleep", "read:workout", "offline"]

# Default callback port for local server
DEFAULT_CALLBACK_PORT = 8642


class WhoopOAuthProvider:
    """Whoop OAuth2 provider using authorization code flow.

    This provider implements the OAuth2 Authorization Code flow for Whoop,
    which requires browser-based authentication. It:
    1. Starts a local callback server
    2. Opens the browser to Whoop's authorization page
    3. Waits for the user to authorize and be redirected back
    4. Exchanges the authorization code for tokens

    Attributes:
        client_id: Whoop OAuth client ID from developer dashboard
        client_secret: Whoop OAuth client secret
        scopes: List of OAuth scopes to request
        callback_port: Port for local callback server (default 8642)
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        scopes: list[str] | None = None,
        callback_port: int = DEFAULT_CALLBACK_PORT,
        http_client: httpx.Client | None = None,
        preferred_browser: str | None = None,
    ) -> None:
        """Initialize the Whoop OAuth provider.

        Args:
            client_id: Whoop OAuth client ID
            client_secret: Whoop OAuth client secret
            scopes: OAuth scopes to request (default: recovery, sleep, workout, offline)
            callback_port: Local port for OAuth callback (default: 8642)
            http_client: Optional httpx client for testing
            preferred_browser: Browser to use for OAuth flow (None = system default)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or DEFAULT_SCOPES
        self.callback_port = callback_port
        self._http_client = http_client or httpx.Client(timeout=30.0)
        self.preferred_browser = preferred_browser

    def obtain_token_interactive(self) -> OAuthTokenResponse | None:
        """Perform authorization code flow with browser interaction.

        This method:
        1. Starts a local callback server
        2. Generates a random state for CSRF protection
        3. Opens the browser to Whoop's authorization page
        4. Prints the URL for manual access if browser doesn't open
        5. Waits for the callback with the authorization code
        6. Exchanges the code for access and refresh tokens

        Returns:
            OAuthTokenResponse with tokens, or None if flow fails
        """
        # Start local callback server
        server = OAuthCallbackServer(port=self.callback_port)
        try:
            redirect_uri = server.start()
        except OSError as e:
            logger.error(
                "whoop_oauth_server_start_failed",
                port=self.callback_port,
                error=str(e),
            )
            return None

        try:
            # Generate state for CSRF protection
            state = secrets.token_urlsafe(32)

            # Build authorization URL
            auth_url = self._build_auth_url(state, redirect_uri)

            logger.info(
                "whoop_oauth_flow_started",
                auth_url=auth_url,
                redirect_uri=redirect_uri,
            )

            # Open browser and print URL
            print("\n🔐 Whoop Authentication Required")
            print("Opening browser for Whoop login...")
            print(f"\n→ {auth_url}\n")
            print("If browser doesn't open, visit the URL above.")

            if not open_browser(auth_url, self.preferred_browser):
                print("⚠️  Could not open browser automatically.")

            print("Waiting for authentication...")

            # Wait for callback
            result = server.wait_for_callback(timeout=300.0)

            if result.error:
                if result.error == "timeout":
                    logger.warning("whoop_oauth_timeout")
                    print("❌ Authentication timed out. Please try again.")
                else:
                    logger.warning("whoop_oauth_error", error=result.error)
                    print(f"❌ Authentication failed: {result.error}")
                return None

            if not result.code:
                logger.error("whoop_oauth_no_code")
                print("❌ No authorization code received.")
                return None

            # Verify state matches
            if result.state != state:
                logger.error(
                    "whoop_oauth_state_mismatch",
                    expected=state,
                    received=result.state,
                )
                print("❌ Security error: State mismatch. Please try again.")
                return None

            # Exchange code for tokens
            token = self._exchange_code(result.code, redirect_uri)
            if token:
                print("✅ Whoop authentication successful!")
            return token

        finally:
            server.stop()

    def refresh_access_token(self, refresh_token: str) -> OAuthTokenResponse | None:
        """Refresh an expired access token.

        Args:
            refresh_token: The refresh token from a previous authentication

        Returns:
            New OAuthTokenResponse with fresh tokens, or None if refresh fails
        """
        logger.info("whoop_oauth_refresh_start")

        try:
            response = self._http_client.post(
                WHOOP_TOKEN_ENDPOINT,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        except httpx.HTTPError as e:
            logger.error("whoop_oauth_refresh_http_error", error=str(e))
            return None

        if response.status_code != 200:
            logger.error(
                "whoop_oauth_refresh_failed",
                status=response.status_code,
                body=response.text,
            )
            return None

        return self._parse_token_response(response.json())

    def _build_auth_url(self, state: str, redirect_uri: str) -> str:
        """Build the Whoop authorization URL.

        Args:
            state: Random state for CSRF protection
            redirect_uri: Local callback URL

        Returns:
            Full authorization URL with query parameters
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
        }
        return f"{WHOOP_AUTH_ENDPOINT}?{urlencode(params)}"

    def _exchange_code(self, code: str, redirect_uri: str) -> OAuthTokenResponse | None:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            redirect_uri: Same redirect URI used in auth request

        Returns:
            OAuthTokenResponse with access and refresh tokens, or None on failure
        """
        logger.info("whoop_oauth_exchange_code")

        try:
            response = self._http_client.post(
                WHOOP_TOKEN_ENDPOINT,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
        except httpx.HTTPError as e:
            logger.error("whoop_oauth_exchange_http_error", error=str(e))
            return None

        if response.status_code != 200:
            logger.error(
                "whoop_oauth_exchange_failed",
                status=response.status_code,
                body=response.text,
            )
            return None

        return self._parse_token_response(response.json())

    def _parse_token_response(self, data: dict[str, Any]) -> OAuthTokenResponse:
        """Parse Whoop token response into OAuthTokenResponse.

        Args:
            data: JSON response from token endpoint

        Returns:
            OAuthTokenResponse with parsed token data
        """
        return OAuthTokenResponse(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in"),
            token_type=data.get("token_type", "bearer"),
        )
