"""Authentication CLI subcommands."""

import json

import click

from pkm_tool.auth import AuthManager
from pkm_tool.auth.browser import open_browser
from pkm_tool.auth.preflight import AuthState, PreflightChecker, SourceAuthStatus
from pkm_tool.config import Config, load_config

from .common import (
    AUTH_SOURCES,
    _build_atlassian_provider,
    _build_google_provider,
    _format_expiry,
    _get_auth_manager,
)


@click.group()
def auth() -> None:
    """Manage authentication credentials."""


@auth.command("list")
def auth_list() -> None:
    """List available authentication sources."""
    click.echo("Available authentication sources:")
    for source, meta in AUTH_SOURCES.items():
        click.echo(f"- {source:12} | {meta['display']:13} | {meta['description']}")


@auth.command("status")
def auth_status() -> None:
    """Display authentication status for all sources."""
    manager = _get_auth_manager()
    tokens = {token.source: token for token in manager.list_tokens()}
    header = f"{'Source':12} {'Status':12} {'Expires At'}"
    click.echo(header)
    click.echo("-" * len(header))
    for source, meta in AUTH_SOURCES.items():
        store_key = meta["store_key"]
        token = tokens.get(store_key)
        status = "authenticated" if token else "missing"
        expires = _format_expiry(token.expires_at if token else None)
        click.echo(f"{meta['display']:12} {status:12} {expires}")


@auth.command("logout")
@click.argument("source", type=click.Choice(list(AUTH_SOURCES.keys())))
def auth_logout(source: str) -> None:
    """Remove stored credentials for a source."""
    meta = AUTH_SOURCES[source]
    store_key = meta["store_key"]
    manager = _get_auth_manager()
    if manager.get_token(store_key) is None:
        click.echo(f"No stored credentials for {meta['display']}.")
        return
    manager.delete_token(store_key)
    click.echo(f"Removed stored credentials for {meta['display']}.")


@auth.command("login")
@click.argument("source", type=click.Choice(list(AUTH_SOURCES.keys())))
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default=None,
    help="Optional configuration file (needed for Google Docs).",
)
def auth_login(source: str, config: str | None) -> None:
    """Interactive authentication workflow for a source."""
    meta = AUTH_SOURCES[source]
    store_key = meta["store_key"]
    manager = _get_auth_manager()

    if source == "atlassian":
        cfg = load_config(config)
        atlas_cfg = cfg.atlassian.config
        # Check if OAuth is configured (client_id + client_secret present)
        has_oauth_config = bool(atlas_cfg.get("client_id") and atlas_cfg.get("client_secret"))

        if has_oauth_config:
            # Use OAuth flow
            try:
                provider = _build_atlassian_provider(config)
                token_response = provider.obtain_token_interactive()
                if token_response is None:
                    raise click.ClickException("Atlassian OAuth authentication failed.")
                manager.save_oauth_token(store_key, token_response)
                click.echo("✅ Atlassian OAuth credentials stored.")
            except click.ClickException:
                raise
            except Exception as e:
                raise click.ClickException(f"Atlassian OAuth failed: {e}") from e
        else:
            # Fall back to API token flow (legacy)
            base_url = click.prompt(
                "Atlassian base URL",
                default=atlas_cfg.get("base_url", "https://example.atlassian.net"),
            )
            username = click.prompt(
                "Atlassian email", default=atlas_cfg.get("username", "user@example.com")
            )
            api_token = click.prompt("Atlassian API token", hide_input=True)
            payload = json.dumps(
                {"base_url": base_url, "username": username, "api_token": api_token}
            )
            manager.store_api_token(store_key, payload, token_type="atlassian_json")
            click.echo("✅ Stored Atlassian API credentials securely.")
        return

    if meta["type"] == "api_token":
        prompt_label = f"{meta['display']} token"
        token = click.prompt(prompt_label, hide_input=True)
        manager.store_api_token(store_key, token, token_type=meta.get("token_type", "api_token"))
        click.echo(f"Stored {meta['display']} credentials securely.")
        return

    if source == "google-docs":
        provider = _build_google_provider(config)
        token_response = provider.obtain_token_interactive()
        if token_response is None:
            raise click.ClickException("Google authentication failed.")
        manager.save_oauth_token(store_key, token_response)
        click.echo("Google Docs credentials stored.")
        return

    raise click.ClickException(f"Unsupported source: {source}")


@auth.command("refresh")
@click.argument("source", type=click.Choice(list(AUTH_SOURCES.keys())))
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default=None,
    help="Optional configuration file (needed for Google Docs).",
)
def auth_refresh(source: str, config: str | None) -> None:
    """Refresh OAuth tokens for a source."""
    meta = AUTH_SOURCES[source]
    store_key = meta["store_key"]
    manager = _get_auth_manager()
    stored = manager.get_token(store_key)

    if meta["type"] != "oauth2":
        raise click.ClickException("Refresh is only supported for OAuth-based sources.")

    if stored is None or not stored.refresh_token:
        raise click.ClickException(
            "No refresh token found. Run `pkm auth login google-docs` first."
        )

    provider = _build_google_provider(config)
    refreshed = provider.refresh_access_token(stored.refresh_token)
    if refreshed is None:
        raise click.ClickException("Token refresh failed.")
    manager.save_oauth_token(store_key, refreshed)
    click.echo("Token refreshed successfully.")


# --- Helpers used by preflight and auth resolution ---


def _try_gh_cli_token() -> str | None:
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
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _get_auth_source_key(source_name: str) -> str | None:
    """Map internal source name to AUTH_SOURCES key."""
    mapping = {
        "github": "github",
        "wakatime": "wakatime",
        "atlassian": "atlassian",
        "google_docs": "google-docs",
        "whoop": "whoop",
    }
    return mapping.get(source_name)


def _perform_auth_login(source: str, config_path: str | None, auth_manager: AuthManager) -> None:
    """Perform authentication login for a source.

    This is a simplified version of auth_login for use in preflight resolution.
    """
    meta = AUTH_SOURCES.get(source)
    if meta is None:
        raise click.ClickException(f"Unknown source: {source}")

    store_key = meta["store_key"]
    cfg = load_config(config_path)

    if source == "atlassian":
        atlas_cfg = cfg.atlassian.config
        # Check if OAuth is configured (client_id + client_secret present)
        has_oauth_config = bool(atlas_cfg.get("client_id") and atlas_cfg.get("client_secret"))

        if has_oauth_config:
            # Use OAuth flow
            try:
                provider = _build_atlassian_provider(config_path)
                token_response = provider.obtain_token_interactive()
                if token_response is None:
                    raise click.ClickException("Atlassian OAuth authentication failed.")
                auth_manager.save_oauth_token(store_key, token_response)
                click.echo("✅ Atlassian OAuth credentials stored.")
            except click.ClickException:
                raise
            except Exception as e:
                raise click.ClickException(f"Atlassian OAuth failed: {e}") from e
        else:
            # No OAuth config - offer guided setup or API token fallback
            click.echo("\n" + "=" * 60)
            click.echo("🔐 Atlassian Authentication Required")
            click.echo("=" * 60)
            click.echo(
                "\nAtlassian recommends OAuth 2.0 for secure, modern authentication."
                "\nBenefits:"
                "\n  ✓ More secure (tokens auto-expire)"
                "\n  ✓ Better user experience (browser-based)"
                "\n  ✓ Automatic token refresh"
                "\n  ✓ No need to manage API tokens manually\n"
            )

            if click.confirm("Set up OAuth authentication? (Recommended)", default=True):
                # Guide user through OAuth app setup
                oauth_app_url = "https://developer.atlassian.com/console/myapps/"
                click.echo("\n📝 Step 1: Create an OAuth 2.0 app")
                click.echo(f"Opening: {oauth_app_url}")
                click.echo(
                    "\nFollow these steps:"
                    "\n  1. Click 'Create' → 'OAuth 2.0 integration'"
                    "\n  2. Enter app name (e.g., 'PKM Tool')"
                    "\n  3. Add callback URL: http://localhost:8643/callback"
                    "\n  4. Add permissions:"
                    "\n     - read:jira-work, read:jira-user"
                    "\n     - read:confluence-content.all, offline_access"
                    "\n  5. Save and note your Client ID and Client secret\n"
                )

                if not open_browser(oauth_app_url, cfg.preferred_browser):
                    click.echo("⚠️  Could not open browser. Please visit the URL above manually.")

                if not click.confirm("\nHave you created the OAuth app?", default=True):
                    click.echo("❌ OAuth setup cancelled.")
                    raise click.Abort()

                # Prompt for OAuth credentials
                click.echo("\n📋 Step 2: Enter your OAuth credentials")
                client_id = click.prompt("Client ID")
                client_secret = click.prompt("Client secret", hide_input=True)

                if not client_id or not client_secret:
                    click.echo("❌ Missing OAuth credentials.")
                    raise click.Abort()

                # Launch OAuth flow
                click.echo("\n🚀 Step 3: Launching browser for authentication...")
                try:
                    from pkm_tool.auth.oauth.atlassian import AtlassianOAuthProvider

                    provider = AtlassianOAuthProvider(
                        client_id,
                        client_secret,
                        preferred_browser=cfg.preferred_browser,
                    )
                    token_response = provider.obtain_token_interactive()
                    if token_response is None:
                        raise click.ClickException("Atlassian OAuth authentication failed.")
                    auth_manager.save_oauth_token(store_key, token_response)
                    click.echo("✅ Atlassian OAuth authentication successful!")
                except Exception as e:
                    raise click.ClickException(f"Atlassian OAuth failed: {e}") from e
            else:
                # Fall back to API token flow (legacy)
                click.echo("\nFalling back to API token authentication...")
                base_url = click.prompt(
                    "Atlassian base URL",
                    default=atlas_cfg.get("base_url", "https://example.atlassian.net"),
                )
                username = click.prompt(
                    "Atlassian email", default=atlas_cfg.get("username", "user@example.com")
                )
                api_token = click.prompt("Atlassian API token", hide_input=True)
                payload = json.dumps(
                    {"base_url": base_url, "username": username, "api_token": api_token}
                )
                auth_manager.store_api_token(store_key, payload, token_type="atlassian_json")
                click.echo("✅ Stored Atlassian API credentials securely.")
        return

    # Special handling for GitHub (gh CLI integration + browser fallback)
    if source == "github":
        token = _try_gh_cli_token()
        if token:
            click.echo("✅ Found authenticated GitHub CLI, using its token")
            auth_manager.store_api_token(store_key, token, token_type="pat")
            return

        # Open browser to PAT creation page
        pat_url = (
            "https://github.com/settings/tokens/new?scopes=repo,read:user&description=pkm-tool"
        )
        click.echo("\nOpening browser to create a Personal Access Token...")
        click.echo(f"→ {pat_url}\n")

        if not open_browser(pat_url, cfg.preferred_browser):
            click.echo("⚠️  Could not open browser automatically.")

        click.echo("Create a token with 'repo' and 'read:user' scopes, then paste it below.")
        token = click.prompt("GitHub token", hide_input=True)
        auth_manager.store_api_token(store_key, token, token_type="pat")
        click.echo("✅ GitHub token stored")
        return

    if meta["type"] == "api_token":
        prompt_label = f"{meta['display']} token"
        token = click.prompt(prompt_label, hide_input=True)
        token_type = meta.get("token_type", "api_token")
        auth_manager.store_api_token(store_key, token, token_type=token_type)
        click.echo(f"Stored {meta['display']} credentials securely.")
        return

    if source == "google-docs":
        provider = _build_google_provider(config_path)
        token_response = provider.obtain_token_interactive()
        if token_response is None:
            raise click.ClickException("Google authentication failed.")
        auth_manager.save_oauth_token(store_key, token_response)
        click.echo("Google Docs credentials stored.")
        return

    raise click.ClickException(f"Unsupported source: {source}")


def _attempt_auth_for_source(
    status: SourceAuthStatus,
    config: Config,
    auth_manager: AuthManager,
    config_path: str | None,
    checker: PreflightChecker,
    auto_oauth: bool,
) -> SourceAuthStatus:
    """Attempt to authenticate a single source."""
    from rich.console import Console

    console = Console()
    source_key = _get_auth_source_key(status.source)
    is_oauth_source = status.source in ("google_docs", "whoop")

    try:
        if is_oauth_source and auto_oauth:
            # OAuth with auto-launch: skip confirmation, go directly to browser
            source_config = getattr(config, status.source, None)
            if source_config:
                return checker._resolve_oauth_source(
                    status.source,
                    source_config,
                    status,
                    interactive=True,
                    skip_confirmation=True,
                )
            return status
        # Traditional flow: use existing auth mechanisms
        if source_key is None:
            console.print(f"[red]Unknown source: {status.source}[/red]")
            return status
        _perform_auth_login(source_key, config_path, auth_manager)
        source_config = getattr(config, status.source, None)
        if source_config:
            return checker.check_source(status.source, source_config)
        return status
    except (click.ClickException, click.Abort):
        console.print(f"[red]Authentication failed for {status.display_name}[/red]")
        return status


def _resolve_missing_auth(
    statuses: list[SourceAuthStatus],
    config: Config,
    auth_manager: AuthManager,
    config_path: str | None,
    *,
    interactive: bool = True,
    auto_oauth: bool = False,
) -> list[SourceAuthStatus]:
    """Attempt to resolve missing/expired authentication interactively."""
    from rich.console import Console

    console = Console()

    if not interactive:
        return statuses

    updated: list[SourceAuthStatus] = []
    checker = PreflightChecker(auth_manager, preferred_browser=config.preferred_browser)

    for status in statuses:
        if status.state not in (AuthState.MISSING, AuthState.EXPIRED):
            updated.append(status)
            continue

        source_key = _get_auth_source_key(status.source)
        if source_key is None:
            updated.append(status)
            continue

        console.print(f"\n[yellow]{status.display_name}[/yellow]: {status.message}")

        # For OAuth sources with auto_oauth, skip the confirmation prompt
        is_oauth_source = status.source in ("google_docs", "whoop", "atlassian")
        should_confirm = not (is_oauth_source and auto_oauth)

        if should_confirm:
            if not click.confirm(f"Would you like to authenticate {status.display_name} now?"):
                updated.append(status)
                continue

        # Attempt authentication using helper
        new_status = _attempt_auth_for_source(
            status, config, auth_manager, config_path, checker, auto_oauth
        )
        updated.append(new_status)

    return updated
