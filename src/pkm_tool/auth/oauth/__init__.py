"""OAuth2 provider implementations."""

from __future__ import annotations

from .base import DeviceCodeResponse, OAuth2Provider, OAuthTokenResponse
from .callback_server import CallbackResult, OAuthCallbackServer
from .google import GoogleOAuthProvider
from .whoop import WhoopOAuthProvider

__all__ = [
    "CallbackResult",
    "DeviceCodeResponse",
    "GoogleOAuthProvider",
    "OAuth2Provider",
    "OAuthCallbackServer",
    "OAuthTokenResponse",
    "WhoopOAuthProvider",
]
