"""Pre-flight authentication check for data sources.

This module provides validation of authentication credentials before
attempting to fetch data from sources. It identifies missing or expired
tokens and can initiate interactive login flows when needed.
"""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

import click
import structlog

from pkm_tool.auth.browser import open_browser
from pkm_tool.auth.manager import AuthManager
from pkm_tool.auth.oauth.google import GoogleOAuthProvider
from pkm_tool.auth.oauth.whoop import WhoopOAuthProvider
from pkm_tool.auth.token_store import StoredToken

if TYPE_CHECKING:
    from pkm_tool.config import Config, SourceConfig

logger = structlog.get_logger(__name__)


class AuthState(Enum):
    """Authentication state for a data source."""

    VALID = "valid"  # Token exists and not expired
    EXPIRED = "expired"  # Token exists but expired (can attempt refresh)
    MISSING = "missing"  # No token at all
    NOT_REQUIRED = "not_required"  # Source doesn't need auth (Calendar, Things)
    INVALID_CONFIG = "invalid_config"  # Config missing required fields
    DISABLED = "disabled"  # Source is disabled in config


@dataclass(slots=True)
class SourceAuthStatus:
    """Authentication status for a single source."""

    source: str
    state: AuthState
    message: str
    display_name: str = ""
    can_refresh: bool = False
    expires_at: datetime | None = None
    missing_fields: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.display_name:
            self.display_name = self.source.replace("_", " ").title()


# Source metadata for authentication requirements
SOURCE_AUTH_INFO: dict[str, dict[str, Any]] = {
    "github": {
        "display": "GitHub",
        "auth_type": "token",
        "store_key": "github",
        "config_key": "token",
        "env_var": "GITHUB_TOKEN",
        "required_fields": [],
    },
    "wakatime": {
        "display": "Wakatime",
        "auth_type": "api_key",
        "store_key": "wakatime",
        "config_key": "api_key",
        "env_var": "WAKATIME_API_KEY",
        "required_fields": [],
    },
    "atlassian": {
        "display": "Atlassian",
        "auth_type": "basic_auth",
        "store_key": "atlassian",
        "config_key": None,  # Uses JSON compound storage
        "env_var": None,
        "required_fields": ["base_url", "username", "api_token"],
    },
    "google_docs": {
        "display": "Google Docs",
        "auth_type": "oauth",
        "store_key": "google_docs",
        "config_key": "access_token",
        "env_var": "GOOGLE_ACCESS_TOKEN",
        "required_fields": [],
        "oauth_config_fields": ["client_id", "client_secret"],
    },
    "whoop": {
        "display": "Whoop",
        "auth_type": "oauth",
        "store_key": "whoop",
        "config_key": "access_token",
        "env_var": "WHOOP_ACCESS_TOKEN",
        "required_fields": [],
        "oauth_config_fields": ["client_id", "client_secret"],
    },
    "apple_calendar": {
        "display": "Apple Calendar",
        "auth_type": "native",
        "platform": "Darwin",
        "required_fields": [],
    },
    "things": {
        "display": "Things",
        "auth_type": "native",
        "platform": "Darwin",
        "required_fields": [],
    },
}


class PreflightChecker:
    """Validates authentication for all enabled data sources.

    Pre-flight checking identifies authentication issues before attempting
    to fetch data, allowing for proactive resolution through interactive
    login flows or clear error reporting.
    """

    def __init__(
        self,
        auth_manager: AuthManager | None = None,
        *,
        refresh_margin_seconds: int = 300,
        preferred_browser: str | None = None,
    ) -> None:
        """Initialize the preflight checker.

        Args:
            auth_manager: AuthManager instance (creates default if None)
            refresh_margin_seconds: Consider tokens expired this many seconds
                before actual expiry (default 5 minutes)
            preferred_browser: Browser to use for OAuth flows (None = system default)
        """
        self.auth_manager = auth_manager or AuthManager()
        self.refresh_margin_seconds = refresh_margin_seconds
        self.preferred_browser = preferred_browser

    def check_all_sources(self, config: Config) -> list[SourceAuthStatus]:
        """Check authentication status for all configured sources.

        Args:
            config: Application configuration

        Returns:
            List of SourceAuthStatus for each source (in config order)
        """
        statuses: list[SourceAuthStatus] = []

        for source_name in config.get_ordered_sources():
            source_config = getattr(config, source_name, None)
            if source_config is None:
                continue

            status = self.check_source(source_name, source_config)
            statuses.append(status)
            logger.debug(
                "preflight_source_checked",
                source=source_name,
                state=status.state.value,
                message=status.message,
            )

        return statuses

    def check_source(self, source_name: str, source_config: SourceConfig) -> SourceAuthStatus:
        """Check authentication status for a single source.

        Args:
            source_name: Name of the source (e.g., "github", "whoop")
            source_config: Configuration for the source

        Returns:
            SourceAuthStatus with the authentication state
        """
        info = SOURCE_AUTH_INFO.get(source_name)
        if info is None:
            return SourceAuthStatus(
                source=source_name,
                state=AuthState.INVALID_CONFIG,
                message=f"Unknown source: {source_name}",
            )

        display_name = info.get("display", source_name)

        # Check if source is disabled
        if not source_config.enabled:
            return SourceAuthStatus(
                source=source_name,
                display_name=display_name,
                state=AuthState.DISABLED,
                message="Disabled in configuration",
            )

        auth_type = info.get("auth_type")

        # Native sources (macOS only)
        if auth_type == "native":
            return self._check_native_source(source_name, info)

        # Token-based sources (API keys, PATs)
        if auth_type in ("token", "api_key"):
            return self._check_token_source(source_name, source_config, info)

        # Basic auth sources (Atlassian)
        if auth_type == "basic_auth":
            return self._check_basic_auth_source(source_name, source_config, info)

        # OAuth sources (Google Docs, Whoop)
        if auth_type == "oauth":
            return self._check_oauth_source(source_name, source_config, info)

        return SourceAuthStatus(
            source=source_name,
            display_name=display_name,
            state=AuthState.INVALID_CONFIG,
            message=f"Unknown auth type: {auth_type}",
        )

    def _check_native_source(self, source_name: str, info: dict[str, Any]) -> SourceAuthStatus:
        """Check platform compatibility for native sources."""
        display_name = info.get("display", source_name)
        required_platform = info.get("platform")

        if required_platform and platform.system() != required_platform:
            return SourceAuthStatus(
                source=source_name,
                display_name=display_name,
                state=AuthState.NOT_REQUIRED,
                message=f"Requires {required_platform} (current: {platform.system()})",
            )

        return SourceAuthStatus(
            source=source_name,
            display_name=display_name,
            state=AuthState.NOT_REQUIRED,
            message="No authentication required",
        )

    def _check_token_source(
        self, source_name: str, source_config: SourceConfig, info: dict[str, Any]
    ) -> SourceAuthStatus:
        """Check token availability for API key/PAT sources."""
        display_name = info.get("display", source_name)
        store_key = info.get("store_key", source_name)
        config_key = info.get("config_key", "token")
        env_var = info.get("env_var")

        # Check token store first
        stored = self.auth_manager.get_token(store_key)
        if stored:
            return self._build_token_status(source_name, display_name, stored)

        # Check config
        config_dict = source_config.config or {}
        if config_key and config_dict.get(config_key):
            return SourceAuthStatus(
                source=source_name,
                display_name=display_name,
                state=AuthState.VALID,
                message="Token configured in config file",
            )

        # Check environment variable
        if env_var and os.environ.get(env_var):
            return SourceAuthStatus(
                source=source_name,
                display_name=display_name,
                state=AuthState.VALID,
                message=f"Token from environment ({env_var})",
            )

        return SourceAuthStatus(
            source=source_name,
            display_name=display_name,
            state=AuthState.MISSING,
            message="No token configured",
        )

    def _check_basic_auth_source(
        self, source_name: str, source_config: SourceConfig, info: dict[str, Any]
    ) -> SourceAuthStatus:
        """Check credentials for basic auth sources (Atlassian)."""
        display_name = info.get("display", source_name)
        store_key = info.get("store_key", source_name)
        required_fields = info.get("required_fields", [])

        # Check token store (stores compound JSON for Atlassian)
        stored = self.auth_manager.get_token(store_key)
        if stored:
            try:
                data = json.loads(stored.token)
                missing = [f for f in required_fields if not data.get(f)]
                if not missing:
                    return SourceAuthStatus(
                        source=source_name,
                        display_name=display_name,
                        state=AuthState.VALID,
                        message="Credentials stored securely",
                    )
                return SourceAuthStatus(
                    source=source_name,
                    display_name=display_name,
                    state=AuthState.INVALID_CONFIG,
                    message=f"Missing fields in stored credentials: {', '.join(missing)}",
                    missing_fields=missing,
                )
            except json.JSONDecodeError:
                pass  # Fall through to config check

        # Check config
        config_dict = source_config.config or {}
        missing = [f for f in required_fields if not config_dict.get(f)]
        if not missing:
            return SourceAuthStatus(
                source=source_name,
                display_name=display_name,
                state=AuthState.VALID,
                message="Credentials configured in config file",
            )

        # Check environment variables
        env_mapping = {
            "base_url": "ATLASSIAN_BASE_URL",
            "username": "ATLASSIAN_USERNAME",
            "api_token": "ATLASSIAN_API_TOKEN",
        }
        for field_name in list(missing):
            env_var = env_mapping.get(field_name)
            if env_var and os.environ.get(env_var):
                missing.remove(field_name)

        if not missing:
            return SourceAuthStatus(
                source=source_name,
                display_name=display_name,
                state=AuthState.VALID,
                message="Credentials from environment variables",
            )

        return SourceAuthStatus(
            source=source_name,
            display_name=display_name,
            state=AuthState.MISSING,
            message=f"Missing: {', '.join(missing)}",
            missing_fields=missing,
        )

    def _check_oauth_source(
        self, source_name: str, source_config: SourceConfig, info: dict[str, Any]
    ) -> SourceAuthStatus:
        """Check OAuth token availability and expiry."""
        display_name = info.get("display", source_name)
        store_key = info.get("store_key", source_name)
        config_key = info.get("config_key", "access_token")
        env_var = info.get("env_var")

        # Check token store first (preferred for OAuth)
        stored = self.auth_manager.get_token(store_key)
        if stored:
            return self._build_token_status(source_name, display_name, stored)

        # Check config for access token
        config_dict = source_config.config or {}
        if config_key and config_dict.get(config_key):
            return SourceAuthStatus(
                source=source_name,
                display_name=display_name,
                state=AuthState.VALID,
                message="Token configured in config file",
            )

        # Check environment variable
        if env_var and os.environ.get(env_var):
            return SourceAuthStatus(
                source=source_name,
                display_name=display_name,
                state=AuthState.VALID,
                message=f"Token from environment ({env_var})",
            )

        # Check if OAuth is configured (can do interactive flow)
        oauth_fields = info.get("oauth_config_fields", [])
        has_oauth_config = all(config_dict.get(f) for f in oauth_fields)

        if has_oauth_config:
            return SourceAuthStatus(
                source=source_name,
                display_name=display_name,
                state=AuthState.MISSING,
                message="No token stored (OAuth configured)",
            )

        return SourceAuthStatus(
            source=source_name,
            display_name=display_name,
            state=AuthState.MISSING,
            message="No token configured",
            missing_fields=oauth_fields if not has_oauth_config else [],
        )

    def _build_token_status(
        self, source_name: str, display_name: str, stored: StoredToken
    ) -> SourceAuthStatus:
        """Build status from a stored token, checking expiry."""
        if stored.expires_at is None:
            # Non-expiring token
            return SourceAuthStatus(
                source=source_name,
                display_name=display_name,
                state=AuthState.VALID,
                message="Token valid (no expiration)",
            )

        now = datetime.now(UTC)
        margin = timedelta(seconds=self.refresh_margin_seconds)

        if stored.expires_at <= now:
            # Already expired
            return SourceAuthStatus(
                source=source_name,
                display_name=display_name,
                state=AuthState.EXPIRED,
                message=f"Token expired at {stored.expires_at.strftime('%Y-%m-%d %H:%M')}",
                can_refresh=bool(stored.refresh_token),
                expires_at=stored.expires_at,
            )

        if stored.expires_at <= now + margin:
            # Expiring soon (within refresh margin)
            return SourceAuthStatus(
                source=source_name,
                display_name=display_name,
                state=AuthState.EXPIRED,
                message=f"Token expires soon ({stored.expires_at.strftime('%H:%M')})",
                can_refresh=bool(stored.refresh_token),
                expires_at=stored.expires_at,
            )

        # Calculate remaining time for display
        remaining = stored.expires_at - now
        if remaining.days > 0:
            time_str = f"{remaining.days} day{'s' if remaining.days > 1 else ''}"
        elif remaining.seconds >= 3600:
            hours = remaining.seconds // 3600
            time_str = f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            minutes = remaining.seconds // 60
            time_str = f"{minutes} minute{'s' if minutes > 1 else ''}"

        return SourceAuthStatus(
            source=source_name,
            display_name=display_name,
            state=AuthState.VALID,
            message=f"Token valid (expires in {time_str})",
            expires_at=stored.expires_at,
        )

    def get_summary(self, statuses: list[SourceAuthStatus]) -> dict[str, int]:
        """Get summary counts by state.

        Args:
            statuses: List of source auth statuses

        Returns:
            Dict mapping state names to counts
        """
        summary: dict[str, int] = {state.value: 0 for state in AuthState}
        for status in statuses:
            summary[status.state.value] += 1
        return summary

    def needs_resolution(self, statuses: list[SourceAuthStatus]) -> list[SourceAuthStatus]:
        """Filter statuses that need authentication resolution.

        Args:
            statuses: List of source auth statuses

        Returns:
            List of statuses with MISSING or EXPIRED state
        """
        return [s for s in statuses if s.state in (AuthState.MISSING, AuthState.EXPIRED)]

    def all_ready(self, statuses: list[SourceAuthStatus]) -> bool:
        """Check if all enabled sources are ready to fetch data.

        Args:
            statuses: List of source auth statuses

        Returns:
            True if all enabled sources have VALID or NOT_REQUIRED state
        """
        for status in statuses:
            if status.state == AuthState.DISABLED:
                continue
            if status.state not in (AuthState.VALID, AuthState.NOT_REQUIRED):
                return False
        return True

    def resolve_missing_auth(
        self,
        statuses: list[SourceAuthStatus],
        config: Config,
        *,
        interactive: bool = True,
    ) -> list[SourceAuthStatus]:
        """Attempt to resolve missing or expired authentication interactively.

        For each source with MISSING or EXPIRED auth:
        - OAuth sources: Try refresh first, then interactive flow
        - API key sources: Prompt user to enter token
        - Basic auth: Prompt for required fields

        Args:
            statuses: List of auth statuses from check_all_sources
            config: Application configuration
            interactive: If True, prompt user for input; if False, only try refresh

        Returns:
            Updated list of statuses after resolution attempts
        """
        needs_resolution = self.needs_resolution(statuses)
        if not needs_resolution:
            logger.debug("preflight_no_resolution_needed")
            return statuses

        logger.info(
            "preflight_resolving_auth",
            sources=[s.source for s in needs_resolution],
            interactive=interactive,
        )

        # Build updated statuses list, replacing resolved ones
        updated_statuses = list(statuses)

        for status in needs_resolution:
            source_name = status.source
            source_config = getattr(config, source_name, None)
            if source_config is None:
                continue

            info = SOURCE_AUTH_INFO.get(source_name)
            if info is None:
                continue

            auth_type = info.get("auth_type")
            new_status: SourceAuthStatus | None = None

            if auth_type == "oauth":
                new_status = self._resolve_oauth_source(
                    source_name, source_config, status, interactive=interactive
                )
            elif source_name == "github":
                # Special handling for GitHub (gh CLI integration + browser fallback)
                new_status = self._resolve_github_source(
                    source_name, source_config, info, interactive=interactive
                )
            elif auth_type in ("token", "api_key"):
                new_status = self._resolve_token_source(
                    source_name, source_config, info, interactive=interactive
                )
            elif auth_type == "basic_auth":
                new_status = self._resolve_basic_auth_source(
                    source_name, source_config, info, interactive=interactive
                )

            # Update status in list if resolution was attempted
            if new_status is not None:
                for i, s in enumerate(updated_statuses):
                    if s.source == source_name:
                        updated_statuses[i] = new_status
                        break

        return updated_statuses

    def _resolve_oauth_source(
        self,
        source_name: str,
        source_config: SourceConfig,
        status: SourceAuthStatus,
        *,
        interactive: bool,
        skip_confirmation: bool = False,
    ) -> SourceAuthStatus:
        """Resolve OAuth source authentication.

        Attempts to refresh existing token first, then falls back to interactive
        flow if configured and allowed.
        """
        config_dict = source_config.config or {}
        display_name = status.display_name

        logger.debug(
            "preflight_resolve_oauth",
            source=source_name,
            can_refresh=status.can_refresh,
            interactive=interactive,
        )

        # Try refresh first if we have a refresh token
        if status.can_refresh:
            stored = self.auth_manager.get_token(source_name)
            if stored and stored.refresh_token:
                provider = self._build_oauth_provider(source_name, config_dict)
                if provider:
                    refreshed = provider.refresh_access_token(stored.refresh_token)
                    if refreshed:
                        self.auth_manager.save_oauth_token(source_name, refreshed)
                        logger.info("preflight_oauth_refresh_success", source=source_name)
                        return self.check_source(source_name, source_config)
                    logger.warning("preflight_oauth_refresh_failed", source=source_name)

        # If non-interactive, return current status
        if not interactive:
            return status

        # Check if we have OAuth config to do interactive flow
        provider = self._build_oauth_provider(source_name, config_dict)
        if provider is None:
            click.echo(
                f"\n{display_name}: Cannot authenticate - "
                "missing client_id or client_secret in config"
            )
            return status

        # Ask user if they want to authenticate (unless confirmation is skipped)
        if not skip_confirmation:
            if not click.confirm(f"\nAuthenticate {display_name}?", default=True):
                return status

        # Run interactive OAuth flow
        if skip_confirmation:
            click.echo(f"\n🌐 Opening browser to authenticate {display_name}...")
        token_response = provider.obtain_token_interactive()
        if token_response:
            self.auth_manager.save_oauth_token(source_name, token_response)
            logger.info("preflight_oauth_interactive_success", source=source_name)
            return self.check_source(source_name, source_config)

        logger.warning("preflight_oauth_interactive_failed", source=source_name)
        return status

    def _resolve_token_source(
        self,
        source_name: str,
        source_config: SourceConfig,
        info: dict[str, Any],
        *,
        interactive: bool,
    ) -> SourceAuthStatus | None:
        """Resolve API token/key source authentication.

        Prompts user to enter their API token if interactive mode is enabled.
        """
        if not interactive:
            return None

        display_name = info.get("display", source_name)
        env_var = info.get("env_var", "")
        hint = f" (or set {env_var})" if env_var else ""

        click.echo(f"\n{display_name}: No API token configured")
        if not click.confirm(f"Enter {display_name} API token now?", default=True):
            return None

        token = click.prompt(f"Enter {display_name} API token", hide_input=True)
        if not token:
            click.echo("No token entered")
            return None

        # Store the token
        self.auth_manager.store_api_token(source_name, token)
        logger.info("preflight_token_stored", source=source_name)
        click.echo(f"{display_name} token stored{hint}")

        return self.check_source(source_name, source_config)

    def _resolve_basic_auth_source(
        self,
        source_name: str,
        source_config: SourceConfig,
        info: dict[str, Any],
        *,
        interactive: bool,
    ) -> SourceAuthStatus | None:
        """Resolve basic auth source authentication (Atlassian).

        Prompts user for all required fields and stores them as JSON.
        """
        if not interactive:
            return None

        display_name = info.get("display", source_name)
        required_fields = info.get("required_fields", [])

        click.echo(f"\n{display_name}: Missing authentication credentials")
        if not click.confirm(f"Enter {display_name} credentials now?", default=True):
            return None

        # Collect all required fields
        credentials: dict[str, str] = {}
        field_prompts = {
            "base_url": ("Base URL", False, "https://your-domain.atlassian.net"),
            "username": ("Username (email)", False, None),
            "api_token": ("API Token", True, None),
        }

        for field_name in required_fields:
            prompt_text, hide, default = field_prompts.get(field_name, (field_name, False, None))
            if default:
                prompt_text = f"{prompt_text} [{default}]"

            value = click.prompt(prompt_text, hide_input=hide, default=default or "")
            if not value:
                click.echo(f"Missing required field: {field_name}")
                return None
            credentials[field_name] = value

        # Store as JSON compound
        credentials_json = json.dumps(credentials)
        self.auth_manager.store_api_token(source_name, credentials_json)
        logger.info("preflight_basic_auth_stored", source=source_name)
        click.echo(f"{display_name} credentials stored securely")

        return self.check_source(source_name, source_config)

    def _try_gh_cli_token(self) -> str | None:
        """Try to get token from gh CLI if installed and authenticated.

        Returns the token string if gh CLI is available and authenticated,
        None otherwise (not installed, not authenticated, or error).
        """
        try:
            import subprocess

            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except FileNotFoundError:
            # gh CLI not installed
            pass
        except subprocess.TimeoutExpired:
            logger.warning("gh_cli_timeout", message="gh auth token timed out")
        except Exception as e:
            logger.warning("gh_cli_error", error=str(e))
        return None

    def _resolve_github_source(
        self,
        source_name: str,
        source_config: SourceConfig,
        info: dict[str, Any],
        *,
        interactive: bool,
    ) -> SourceAuthStatus | None:
        """Resolve GitHub authentication with gh CLI integration.

        Strategy:
        1. Try `gh auth token` if gh CLI is installed and authenticated
        2. Fall back to opening browser to PAT creation page
        3. Prompt for manual token entry
        """
        if not interactive:
            return None

        display_name = info.get("display", source_name)
        click.echo(f"\n{display_name}: No API token configured")

        # Try gh CLI first (silent check)
        token = self._try_gh_cli_token()
        if token:
            click.echo("✅ Found authenticated GitHub CLI, using its token")
            self.auth_manager.store_api_token(source_name, token)
            logger.info("preflight_github_gh_cli_success", source=source_name)
            return self.check_source(source_name, source_config)

        # Ask user how to proceed
        if not click.confirm(f"Authenticate {display_name}?", default=True):
            return None

        # Open browser to PAT creation page
        pat_url = (
            "https://github.com/settings/tokens/new?scopes=repo,read:user&description=pkm-tool"
        )
        click.echo("\nOpening browser to create a Personal Access Token...")
        click.echo(f"→ {pat_url}\n")

        if not open_browser(pat_url, self.preferred_browser):
            click.echo("⚠️  Could not open browser automatically.")

        click.echo("Create a token with 'repo' and 'read:user' scopes, then paste it below.")
        token = click.prompt("Enter GitHub token", hide_input=True)

        if not token:
            click.echo("No token entered")
            return None

        self.auth_manager.store_api_token(source_name, token)
        logger.info("preflight_github_token_stored", source=source_name)
        click.echo("✅ GitHub token stored")
        return self.check_source(source_name, source_config)

    def _build_oauth_provider(
        self, source_name: str, config_dict: dict[str, Any]
    ) -> GoogleOAuthProvider | WhoopOAuthProvider | None:
        """Build the appropriate OAuth provider for a source.

        Returns None if required OAuth config (client_id, client_secret) is missing.
        """
        client_id = config_dict.get("client_id")
        client_secret = config_dict.get("client_secret")

        if not client_id or not client_secret:
            return None

        if source_name == "google_docs":
            return GoogleOAuthProvider(
                client_id,
                client_secret=client_secret,
                scopes=config_dict.get("scopes"),
            )
        if source_name == "whoop":
            return WhoopOAuthProvider(
                client_id,
                client_secret,
                scopes=config_dict.get("scopes"),
                callback_port=config_dict.get("callback_port", 8642),
                preferred_browser=self.preferred_browser,
            )
        return None
