"""High-level authentication orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog

from pkm_tool.auth.token_store import StoredToken, TokenStore

if TYPE_CHECKING:
    from pkm_tool.auth.oauth.base import OAuth2Provider, OAuthTokenResponse

logger = structlog.get_logger(__name__)


class AuthManager:
    """Coordinates token storage, refresh, and interactive authentication flows."""

    def __init__(
        self, token_store: TokenStore | None = None, *, refresh_margin_seconds: int = 300
    ) -> None:
        self.token_store = token_store or TokenStore()
        self.refresh_margin_seconds = refresh_margin_seconds

    # -------------------------------------------------------------------------
    # Generic token helpers
    # -------------------------------------------------------------------------
    def get_token(self, source: str) -> StoredToken | None:
        """Return decrypted token for a source if it exists."""
        return self.token_store.get_token(source)

    def list_tokens(self) -> list[StoredToken]:
        """Return a list of decrypted tokens for displaying status information."""
        return self.token_store.list_tokens()

    def delete_token(self, source: str) -> None:
        """Remove credentials for a given source."""
        logger.info("auth_token_deleted", source=source)
        self.token_store.delete_token(source)

    def validate_token(self, source: str) -> tuple[bool, str]:
        """
        Validate if a token exists and is not expired.

        Args:
            source: The source name (e.g., "github", "whoop")

        Returns:
            Tuple of (is_valid, message) where is_valid is True if token
            exists and hasn't expired, and message provides details.
        """
        stored = self.token_store.get_token(source)

        if stored is None:
            return (False, "No token stored")

        if stored.expires_at is None:
            return (True, "Token valid (no expiration)")

        if self._needs_refresh(stored):
            return (False, f"Token expired at {stored.expires_at.isoformat()}")

        # Token is valid with expiration - calculate time remaining
        now = datetime.now(UTC)
        remaining = stored.expires_at - now
        return (True, f"Token valid (expires in {self._format_duration(remaining)})")

    def store_api_token(
        self, source: str, token: str, *, token_type: str = "api_key"
    ) -> StoredToken:
        """Persist an API token (PAT, API key, etc.) and return the stored record."""
        logger.info("auth_store_api_token", source=source, token_type=token_type)
        self.token_store.save_token(source, token, token_type=token_type)
        stored = self.token_store.get_token(source)
        if stored is None:
            raise RuntimeError("Token storage failed")
        return stored

    # -------------------------------------------------------------------------
    # OAuth2 helpers
    # -------------------------------------------------------------------------
    def ensure_oauth_token(
        self,
        source: str,
        provider: OAuth2Provider,
        *,
        allow_interactive: bool = False,
    ) -> StoredToken | None:
        """
        Ensure a valid OAuth token exists.

        Attempt in order:
        1. Use cached token if still valid
        2. Refresh using refresh token
        3. (Optional) Trigger interactive flow if allowed
        """
        logger.debug(
            "auth_ensure_oauth_token",
            source=source,
            allow_interactive=allow_interactive,
        )
        stored = self.token_store.get_token(source)

        if stored and not self._needs_refresh(stored):
            return stored

        if stored and stored.refresh_token:
            refreshed = provider.refresh_access_token(stored.refresh_token)
            if refreshed:
                return self._persist_oauth_token(source, refreshed)

        if allow_interactive:
            new_token = provider.obtain_token_interactive()
            if new_token:
                return self._persist_oauth_token(source, new_token)

        if stored is None:
            logger.warning("auth_token_missing", source=source)
        else:
            logger.warning(
                "auth_token_expired", source=source, has_refresh=bool(stored.refresh_token)
            )
        return stored

    def save_oauth_token(self, source: str, token: OAuthTokenResponse) -> StoredToken:
        """Persist an OAuth token response."""
        return self._persist_oauth_token(source, token)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------
    def _persist_oauth_token(self, source: str, token: OAuthTokenResponse) -> StoredToken:
        expires_at = None
        if token.expires_in is not None:
            expires_at = datetime.now(UTC) + timedelta(seconds=token.expires_in)

        self.token_store.save_token(
            source,
            token.access_token,
            refresh_token=token.refresh_token,
            expires_at=expires_at,
            token_type=token.token_type,
        )
        logger.info(
            "auth_token_saved",
            source=source,
            expires_at=expires_at.isoformat() if expires_at else None,
        )
        stored = self.token_store.get_token(source)
        if stored is None:
            raise RuntimeError("Token storage failed")
        return stored

    def _needs_refresh(self, stored: StoredToken) -> bool:
        if stored.expires_at is None:
            return False

        margin = timedelta(seconds=self.refresh_margin_seconds)
        now = datetime.now(UTC)
        return stored.expires_at <= now + margin

    def _format_duration(self, delta: timedelta) -> str:
        """Format a timedelta into a human-readable string (e.g., '2 hours', '3 days')."""
        total_seconds = int(delta.total_seconds())

        if total_seconds < 0:
            return "expired"

        if total_seconds < 60:
            return f"{total_seconds} seconds" if total_seconds != 1 else "1 second"

        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes} minutes" if minutes != 1 else "1 minute"

        hours = minutes // 60
        if hours < 24:
            return f"{hours} hours" if hours != 1 else "1 hour"

        days = hours // 24
        return f"{days} days" if days != 1 else "1 day"
