"""Google OAuth2 provider using device code flow."""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog

from pkm_tool.auth.oauth.base import DeviceCodeResponse, OAuth2Provider, OAuthTokenResponse

logger = structlog.get_logger(__name__)

GOOGLE_DEVICE_CODE_ENDPOINT = "https://oauth2.googleapis.com/device/code"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
DEFAULT_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class GoogleOAuthProvider(OAuth2Provider):
    """Implements Google OAuth2 device code flow."""

    def __init__(
        self,
        client_id: str,
        *,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or DEFAULT_SCOPES
        self._http_client = http_client or httpx.Client(timeout=30.0)

    def obtain_token_interactive(self) -> OAuthTokenResponse | None:
        """Perform device code flow and return tokens."""
        device_code = self._start_device_flow()
        if device_code is None:
            return None

        logger.info(
            "google_oauth_device_flow_started",
            verification_uri=device_code.verification_uri,
            user_code=device_code.user_code,
            expires_in=device_code.expires_in,
        )
        print(f"Visit {device_code.verification_uri} and enter the code: {device_code.user_code}")

        return self._poll_for_token(device_code)

    def refresh_access_token(self, refresh_token: str) -> OAuthTokenResponse | None:
        """Refresh Google OAuth token."""
        logger.info("google_oauth_refresh_start")
        response = self._http_client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if response.status_code != 200:
            logger.error(
                "google_oauth_refresh_failed", status=response.status_code, body=response.text
            )
            return None

        return self._parse_token_response(response.json())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start_device_flow(self) -> DeviceCodeResponse | None:
        try:
            response = self._http_client.post(
                GOOGLE_DEVICE_CODE_ENDPOINT,
                data={
                    "client_id": self.client_id,
                    "scope": " ".join(self.scopes),
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("google_device_flow_start_failed", error=str(exc))
            return None

        data = response.json()
        return DeviceCodeResponse(
            user_code=data["user_code"],
            device_code=data["device_code"],
            verification_uri=data["verification_url"],
            expires_in=data["expires_in"],
            interval=data.get("interval", 5),
        )

    def _poll_for_token(self, device_code: DeviceCodeResponse) -> OAuthTokenResponse | None:
        logger.info("google_oauth_polling_for_token")
        deadline = time.time() + device_code.expires_in

        while time.time() < deadline:
            time.sleep(device_code.interval)
            response = self._http_client.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "device_code": device_code.device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            )

            if response.status_code == 200:
                return self._parse_token_response(response.json())

            data = response.json()
            error = data.get("error")
            if error == "authorization_pending":
                continue
            if error == "slow_down":
                device_code.interval += 5
                continue

            logger.error("google_oauth_device_flow_failed", error=error, details=data)
            return None

        logger.error("google_oauth_device_flow_timeout")
        return None

    def _parse_token_response(self, data: dict[str, Any]) -> OAuthTokenResponse:
        return OAuthTokenResponse(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in"),
            token_type=data.get("token_type", "bearer"),
        )
