"""Shared OAuth2 provider dataclasses and protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class DeviceCodeResponse:
    """Response from an OAuth2 device code initiation request."""

    user_code: str
    device_code: str
    verification_uri: str
    expires_in: int
    interval: int


@dataclass(slots=True)
class OAuthTokenResponse:
    """Represents an OAuth access token response."""

    access_token: str
    refresh_token: str | None
    expires_in: int | None
    token_type: str = "bearer"


class OAuth2Provider(Protocol):
    """Protocol for OAuth2 providers."""

    def obtain_token_interactive(self) -> OAuthTokenResponse | None:
        """Run the full device code flow and return an access token."""

    def refresh_access_token(self, refresh_token: str) -> OAuthTokenResponse | None:
        """Refresh an access token using a refresh token."""
