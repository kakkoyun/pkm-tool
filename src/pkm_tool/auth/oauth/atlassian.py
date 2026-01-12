"""Atlassian OAuth2 provider using OAuth 2.0 (3LO) authorization code flow.

Atlassian uses the standard OAuth2 Authorization Code flow (3-legged OAuth), which requires:
1. Opening a browser for user authentication
2. Receiving the authorization code via a local callback server
3. Exchanging the code for access and refresh tokens

Reference: https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/
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

# Atlassian OAuth2 endpoints
ATLASSIAN_AUTH_ENDPOINT = "https://auth.atlassian.com/authorize"
ATLASSIAN_TOKEN_ENDPOINT = "https://auth.atlassian.com/oauth/token"

# Default OAuth scopes for Atlassian (Jira + Confluence read access)
DEFAULT_SCOPES = [
    "read:jira-work",
    "read:jira-user",
    "read:confluence-content.all",
    "offline_access",
]

# Default callback port for local server
DEFAULT_CALLBACK_PORT = 8643


class AtlassianOAuthProvider:
    """Atlassian OAuth2 provider using authorization code flow (3LO).

    This provider implements the OAuth2 Authorization Code flow for Atlassian,
    which requires browser-based authentication. It:
    1. Starts a local callback server
    2. Opens the browser to Atlassian's authorization page
    3. Waits for the user to authorize and be redirected back
    4. Exchanges the authorization code for tokens

    Attributes:
        client_id: Atlassian OAuth client ID from developer console
        client_secret: Atlassian OAuth client secret
        scopes: List of OAuth scopes to request
        callback_port: Port for local callback server (default 8643)
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
        """Initialize the Atlassian OAuth provider.

        Args:
            client_id: Atlassian OAuth client ID
            client_secret: Atlassian OAuth client secret
            scopes: OAuth scopes to request (default: Jira + Confluence read access)
            callback_port: Local port for OAuth callback (default: 8643)
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
        3. Opens the browser to Atlassian's authorization page
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
            logger.error("callback_server_failed", error=str(e), port=self.callback_port)
            print(f"❌ Failed to start callback server on port {self.callback_port}: {e}")
            return None

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Build authorization URL
        auth_params = {
            "audience": "api.atlassian.com",
            "client_id": self.client_id,
            "scope": " ".join(self.scopes),
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        }
        auth_url = f"{ATLASSIAN_AUTH_ENDPOINT}?{urlencode(auth_params)}"

        # Open browser
        logger.info("atlassian_oauth_starting", scopes=self.scopes)
        print("\n🔐 Opening browser to authenticate with Atlassian...")
        print(f"If browser doesn't open automatically, visit:\n{auth_url}\n")

        if not open_browser(auth_url, self.preferred_browser):
            print("⚠️  Could not open browser automatically.")
            print(f"Please visit: {auth_url}")

        # Wait for callback
        print("Waiting for authorization... (this may take a minute)")
        try:
            result = server.wait_for_callback(timeout=300)  # 5 minutes
        except TimeoutError:
            logger.error("atlassian_oauth_timeout")
            print("\n❌ Timeout waiting for authorization")
            return None
        finally:
            server.stop()

        # Check for errors in callback
        if result.error:
            logger.error("atlassian_oauth_error", error=result.error)
            print(f"\n❌ Authorization failed: {result.error}")
            return None

        # Verify state matches
        if result.state != state:
            logger.error("atlassian_oauth_state_mismatch", expected=state, received=result.state)
            print("\n❌ Invalid state parameter (possible CSRF attack)")
            return None

        # Get authorization code
        if not result.code:
            logger.error("atlassian_oauth_no_code")
            print("\n❌ No authorization code received")
            return None

        # Exchange code for tokens
        logger.info("atlassian_oauth_exchanging_code")
        return self._exchange_code(result.code, redirect_uri)

    def _exchange_code(self, code: str, redirect_uri: str) -> OAuthTokenResponse | None:
        """Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from callback
            redirect_uri: The redirect URI used in the authorization request

        Returns:
            OAuthTokenResponse with tokens, or None if exchange fails
        """
        token_data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }

        try:
            response = self._http_client.post(ATLASSIAN_TOKEN_ENDPOINT, json=token_data)
            response.raise_for_status()
            token_json = response.json()

            logger.info(
                "atlassian_oauth_success", has_refresh=bool(token_json.get("refresh_token"))
            )
            print("✅ Successfully authenticated with Atlassian")

            return self._parse_token_response(token_json)
        except httpx.HTTPStatusError as e:
            logger.error("atlassian_token_exchange_failed", status=e.response.status_code)
            print(f"\n❌ Token exchange failed: {e.response.status_code}")
            try:
                error_details = e.response.json()
                print(f"Error: {error_details}")
            except Exception:
                print(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error("atlassian_token_exchange_error", error=str(e))
            print(f"\n❌ Token exchange error: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> OAuthTokenResponse | None:
        """Refresh an expired access token using the refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            OAuthTokenResponse with new tokens, or None if refresh fails
        """
        token_data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }

        try:
            response = self._http_client.post(ATLASSIAN_TOKEN_ENDPOINT, json=token_data)
            response.raise_for_status()
            token_json = response.json()

            logger.info("atlassian_refresh_success")
            return self._parse_token_response(token_json)
        except httpx.HTTPStatusError as e:
            logger.error("atlassian_refresh_failed", status=e.response.status_code)
            return None
        except Exception as e:
            logger.error("atlassian_refresh_error", error=str(e))
            return None

    def _parse_token_response(self, token_json: dict[str, Any]) -> OAuthTokenResponse | None:
        """Parse token response from Atlassian API.

        Args:
            token_json: JSON response from token endpoint

        Returns:
            OAuthTokenResponse or None if required fields missing
        """
        access_token = token_json.get("access_token")
        if not access_token:
            logger.error("atlassian_no_access_token")
            return None

        return OAuthTokenResponse(
            access_token=access_token,
            refresh_token=token_json.get("refresh_token"),
            expires_in=token_json.get("expires_in"),
            token_type=token_json.get("token_type", "Bearer"),
        )
