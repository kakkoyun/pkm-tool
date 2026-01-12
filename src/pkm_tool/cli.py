"""CLI entry point for PKM tool."""

import datetime as dt
import functools
import json
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
from dateutil import parser as date_parser

if TYPE_CHECKING:
    from pkm_tool.auth.oauth.atlassian import AtlassianOAuthProvider

from pkm_tool.aggregator import aggregate_data
from pkm_tool.auth import AuthManager
from pkm_tool.auth.browser import open_browser
from pkm_tool.auth.oauth import GoogleOAuthProvider
from pkm_tool.auth.preflight import AuthState, PreflightChecker, SourceAuthStatus
from pkm_tool.config import Config, load_config
from pkm_tool.formatters import (
    format_as_json,
    format_as_markdown,
    format_filename,
    write_report_to_file,
)
from pkm_tool.logging import configure_logging, get_logger
from pkm_tool.models import AggregatedData
from pkm_tool.sources.apple_calendar import fetch_calendar_events
from pkm_tool.sources.atlassian import fetch_atlassian_items
from pkm_tool.sources.github import fetch_github_activities
from pkm_tool.sources.google_docs import fetch_google_docs
from pkm_tool.sources.things import fetch_things_tasks
from pkm_tool.sources.wakatime import fetch_wakatime_activities
from pkm_tool.sources.whoop import (
    fetch_whoop_recovery,
    fetch_whoop_sleep,
    fetch_whoop_workouts,
)

AUTH_SOURCES: dict[str, dict[str, Any]] = {
    "github": {
        "store_key": "github",
        "display": "GitHub",
        "type": "api_token",
        "token_type": "pat",
        "description": "GitHub personal access token with repo read access.",
    },
    "wakatime": {
        "store_key": "wakatime",
        "display": "Wakatime",
        "type": "api_token",
        "token_type": "api_key",
        "description": "Wakatime API key from https://wakatime.com/settings/api-key.",
    },
    "atlassian": {
        "store_key": "atlassian",
        "display": "Atlassian",
        "type": "compound",
        "description": "Atlassian Cloud credentials (base URL, email, API token).",
    },
    "google-docs": {
        "store_key": "google_docs",
        "display": "Google Docs",
        "type": "oauth2",
        "description": "Google Drive OAuth (device code flow). Requires client_id in config.",
    },
    "whoop": {
        "store_key": "whoop",
        "display": "Whoop",
        "type": "api_token",
        "token_type": "oauth_access",
        "description": "Paste Whoop OAuth access token from developer.whoop.com.",
    },
}

_AUTH_MANAGER: AuthManager | None = None


def _get_auth_manager() -> AuthManager:
    global _AUTH_MANAGER
    if _AUTH_MANAGER is None:
        _AUTH_MANAGER = AuthManager()
    return _AUTH_MANAGER


def _format_expiry(timestamp: datetime | None) -> str:
    if timestamp is None:
        return "n/a"
    return timestamp.isoformat()


def _build_google_provider(config_path: str | None) -> GoogleOAuthProvider:
    cfg = load_config(config_path)
    google_cfg = cfg.google_docs.config
    client_id = google_cfg.get("client_id")
    if not client_id:
        raise click.ClickException(
            "Google Docs client_id missing. Add it under google_docs.config.client_id."
        )
    client_secret = google_cfg.get("client_secret")
    scopes = google_cfg.get("scopes") or [
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    if isinstance(scopes, str):
        scopes = [scopes]

    # Note: Google OAuth uses device code flow (no browser opening), so no preferred_browser needed
    return GoogleOAuthProvider(
        client_id,
        client_secret=client_secret,
        scopes=scopes,
    )


def _build_atlassian_provider(config_path: str | None) -> "AtlassianOAuthProvider":
    """Build Atlassian OAuth provider from config.

    Args:
        config_path: Path to config file

    Returns:
        Configured AtlassianOAuthProvider

    Raises:
        click.ClickException: If required OAuth config is missing
    """
    from pkm_tool.auth.oauth.atlassian import AtlassianOAuthProvider

    cfg = load_config(config_path)
    atlassian_cfg = cfg.atlassian.config
    client_id = atlassian_cfg.get("client_id")
    if not client_id:
        raise click.ClickException(
            "Atlassian client_id missing. Add it under atlassian.config.client_id."
        )
    client_secret = atlassian_cfg.get("client_secret")
    if not client_secret:
        raise click.ClickException(
            "Atlassian client_secret missing. Add it under atlassian.config.client_secret."
        )

    # Optional configuration
    scopes = atlassian_cfg.get("scopes")
    callback_port = atlassian_cfg.get("callback_port", 8643)

    # Get preferred browser: per-source preference or global fallback
    preferred_browser = cfg.atlassian.preferred_browser or cfg.preferred_browser

    return AtlassianOAuthProvider(
        client_id,
        client_secret,
        scopes=scopes,
        callback_port=callback_port,
        preferred_browser=preferred_browser,
    )


# Common options decorator for all subcommands
def common_options(func: Callable) -> Callable:
    """Decorator to add common CLI options to subcommands."""

    @click.option(
        "--date",
        "-d",
        default=None,
        help="Date to fetch data for (default: today). Format: YYYY-MM-DD or natural language.",
    )
    @click.option(
        "--from",
        "from_date",
        default=None,
        help="Start date for date range (requires --to). Format: YYYY-MM-DD or natural language.",
    )
    @click.option(
        "--to",
        "to_date",
        default=None,
        help="End date for date range (requires --from). Format: YYYY-MM-DD or natural language.",
    )
    @click.option(
        "--output-dir",
        "-o",
        default=None,
        help="Output directory for batch mode (date ranges). Overrides config setting.",
    )
    @click.option(
        "--exclude-weekends",
        is_flag=True,
        default=False,
        help="Skip weekends (Saturdays and Sundays) in date ranges and source fetching.",
    )
    @click.option(
        "--format",
        "-f",
        type=click.Choice(["markdown", "json"], case_sensitive=False),
        default="markdown",
        help="Output format (default: markdown)",
    )
    @click.option(
        "--config",
        "-c",
        type=click.Path(exists=True),
        default=None,
        help="Path to configuration file",
    )
    @click.option(
        "--verbose",
        "-v",
        is_flag=True,
        default=False,
        help="Enable verbose (DEBUG) logging",
    )
    @click.option(
        "--log-format",
        type=click.Choice(["human", "json"], case_sensitive=False),
        default="human",
        help="Log output format (default: human)",
    )
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return wrapper


def _parse_relative_date(date_input: str) -> date | None:
    """
    Parse relative date strings like 'yesterday', 'today', 'tomorrow'.

    Args:
        date_input: Relative date string (case-insensitive)

    Returns:
        Parsed date object or None if not a recognized relative date
    """
    from datetime import timedelta

    today = datetime.now().date()
    normalized = date_input.lower().strip()

    # Mapping of relative date keywords to timedelta offsets
    relative_dates = {
        "today": timedelta(days=0),
        "yesterday": timedelta(days=-1),
        "tomorrow": timedelta(days=1),
    }

    if normalized in relative_dates:
        return today + relative_dates[normalized]

    return None


def _parse_date(date_input: str | None, logger: Any) -> date:
    """
    Parse date string into date object.

    Supports:
    - None: returns today's date
    - Relative dates: 'yesterday', 'today', 'tomorrow' (case-insensitive)
    - Absolute dates: YYYY-MM-DD, natural language via dateutil

    Args:
        date_input: Date string or None for today
        logger: Logger instance for logging

    Returns:
        Parsed date object

    Raises:
        click.Abort: If date parsing fails
    """
    if date_input is None:
        target_date = datetime.now().date()
        logger.debug("using_today_as_target_date", date=str(target_date))
        return target_date

    # Try relative date parsing first (yesterday, today, tomorrow)
    relative_result = _parse_relative_date(date_input)
    if relative_result is not None:
        logger.debug("parsed_relative_date", input=date_input, parsed=str(relative_result))
        return relative_result

    # Fall back to dateutil for absolute dates
    try:
        parsed_date = date_parser.parse(date_input)
        target_date = parsed_date.date()
        logger.debug("parsed_date", input=date_input, parsed=str(target_date))
        return target_date
    except (ValueError, TypeError) as e:
        logger.error("date_parsing_failed", error=str(e), input=date_input)
        click.echo(f"Error parsing date: {e}", err=True)
        raise click.Abort()


def _generate_date_range(from_date: date, to_date: date, exclude_weekends: bool) -> list[date]:
    """
    Generate list of dates in range.

    Args:
        from_date: Start date (inclusive)
        to_date: End date (inclusive)
        exclude_weekends: Skip Saturdays (5) and Sundays (6)

    Returns:
        List of dates in range
    """
    dates = []
    current = from_date
    while current <= to_date:
        if not exclude_weekends or current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def _fetch_single_source(
    source_name: str,
    fetch_func: Any,
    target_date: date,
    config: Any,
    logger: Any,
) -> AggregatedData:
    """
    Fetch data from a single source.

    Args:
        source_name: Name of the source for logging
        fetch_func: Function to fetch data from source
        target_date: Date to fetch data for
        config: Configuration object
        logger: Logger instance

    Returns:
        AggregatedData with single source populated

    Raises:
        click.Abort: If fetching fails
    """
    data = AggregatedData(date=target_date)

    logger.info("fetching_source", source=source_name)
    start_time = time.time()
    try:
        result = fetch_func(target_date, config)
        duration = time.time() - start_time

        # Populate the appropriate field in AggregatedData
        if source_name == "apple_calendar":
            data.calendar_events = result
        elif source_name == "github":
            data.github_activities = result
        elif source_name == "atlassian":
            data.atlassian_items = result
        elif source_name == "things":
            data.things_tasks = result
        elif source_name == "wakatime":
            data.wakatime_activities = result
        elif source_name == "google_docs":
            data.google_docs = result
        elif source_name == "whoop":
            # For Whoop, result is a tuple of (recovery, sleep, workouts)
            data.whoop_recovery, data.whoop_sleep, data.whoop_workouts = result

        logger.info(
            "source_fetch_completed",
            source=source_name,
            duration_seconds=f"{duration:.2f}",
            items_count=len(result),
        )
        return data
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "source_fetch_failed",
            source=source_name,
            error=str(e),
            duration_seconds=f"{duration:.2f}",
            exc_info=True,
        )
        click.echo(f"Error fetching {source_name}: {e}", err=True)
        raise click.Abort()


def _format_and_output(
    data: AggregatedData,
    format: str,
    logger: Any,
    config: Config | None = None,
) -> None:
    """
    Format data and output to stdout.

    Args:
        data: AggregatedData to format
        format: Output format (markdown or json)
        logger: Logger instance
        config: Optional config for titles and order
    """
    logger.debug("formatting_output", format=format)
    if format.lower() == "json":
        output = format_as_json(data)
    else:
        output = format_as_markdown(data, config)
    click.echo(output)
    logger.info("pkm_tool_completed", output_format=format)


def _process_batch_or_single(
    source_name: str,
    fetch_func: Any,
    date: str | None,
    from_date: str | None,
    to_date: str | None,
    output_dir: str | None,
    exclude_weekends: bool,
    format: str,
    config: str | None,
    source_config: Any,
    logger: Any,
) -> None:
    """
    Process either batch mode (date range) or single-day mode for a source.

    Args:
        source_name: Name of the source
        fetch_func: Function to fetch data from source
        date: Single date option
        from_date: Start of date range
        to_date: End of date range
        output_dir: Output directory override
        exclude_weekends: Whether to exclude weekends
        format: Output format
        config: Config file path
        source_config: Source-specific config dict
        logger: Logger instance
    """
    # Validate date options
    _validate_date_options(date, from_date, to_date, logger)

    # Load config for output settings
    cfg = load_config(config)

    # Check if batch mode (date range) or single-day mode
    if from_date and to_date:
        # Batch mode: generate files for date range
        start_date = _parse_date(from_date, logger)
        end_date = _parse_date(to_date, logger)

        if start_date > end_date:
            logger.error("invalid_date_range", reason="Start date must be <= end date")
            raise click.ClickException("Start date must be before or equal to end date.")

        dates = _generate_date_range(start_date, end_date, exclude_weekends)
        output_directory = Path(output_dir or cfg.output_directory)

        logger.info(
            "batch_mode_started",
            source=source_name,
            date_count=len(dates),
            output_directory=str(output_directory),
        )

        for target_date in dates:
            try:
                logger.info("fetching_date", source=source_name, date=str(target_date))

                # Create AggregatedData and populate appropriate field
                data = AggregatedData(date=target_date)
                result = fetch_func(target_date, source_config)

                # Populate the appropriate field based on source name
                if source_name == "apple_calendar":
                    data.calendar_events = result
                elif source_name == "github":
                    data.github_activities = result
                elif source_name == "atlassian":
                    data.atlassian_items = result
                elif source_name == "things":
                    data.things_tasks = result
                elif source_name == "wakatime":
                    data.wakatime_activities = result
                elif source_name == "google_docs":
                    data.google_docs = result
                elif source_name == "whoop":
                    # For Whoop, result is a tuple of (recovery, sleep, workouts)
                    data.whoop_recovery, data.whoop_sleep, data.whoop_workouts = result

                # Format filename
                filename = format_filename(cfg.output_filename_template, target_date, format)
                output_path = output_directory / filename

                # Write with smart merge
                write_report_to_file(data, output_path, format, merge_existing=True, config=cfg)
                logger.info("report_written", path=str(output_path))
            except Exception as e:
                logger.error(
                    "date_fetch_failed", date=str(target_date), error=str(e), exc_info=True
                )
                click.echo(f"Error processing {target_date}: {e}", err=True)

        click.echo(f"Generated {len(dates)} reports in {output_directory}/")
        logger.info("batch_mode_completed", source=source_name, date_count=len(dates))
    else:
        # Single-day mode: output to stdout
        target_date = _parse_date(date, logger)
        data = _fetch_single_source(source_name, fetch_func, target_date, source_config, logger)
        _format_and_output(data, format, logger, cfg)


def _validate_date_options(
    date: str | None, from_date: str | None, to_date: str | None, logger: Any
) -> None:
    """
    Validate date options combinations.

    Args:
        date: Single date option
        from_date: Start of date range
        to_date: End of date range
        logger: Logger instance

    Raises:
        click.ClickException: If options are invalid
    """
    # Check for conflicting options
    if date and (from_date or to_date):
        logger.error("invalid_date_options", reason="Cannot use --date with --from/--to")
        raise click.ClickException("Cannot use --date with --from/--to. Use one or the other.")

    # Check that both from and to are provided together
    if (from_date and not to_date) or (to_date and not from_date):
        logger.error("invalid_date_range", reason="Both --from and --to must be provided")
        raise click.ClickException("Both --from and --to must be provided for date ranges.")


def _display_auth_status(statuses: list[SourceAuthStatus]) -> None:
    """Display authentication status for all sources."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    console.print("\n[bold]Pre-flight Authentication Check[/bold]")
    console.print("-" * 40)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Status", style="bold", width=3)
    table.add_column("Source", width=15)
    table.add_column("Message")

    state_symbols = {
        AuthState.VALID: ("[green]OK[/green]", "green"),
        AuthState.EXPIRED: ("[yellow]![/yellow]", "yellow"),
        AuthState.MISSING: ("[red]X[/red]", "red"),
        AuthState.NOT_REQUIRED: ("[dim]-[/dim]", "dim"),
        AuthState.INVALID_CONFIG: ("[red]X[/red]", "red"),
        AuthState.DISABLED: ("[dim]-[/dim]", "dim"),
    }

    for status in statuses:
        symbol, style = state_symbols.get(status.state, ("?", ""))
        table.add_row(
            symbol,
            f"[{style}]{status.display_name}[/{style}]",
            f"[{style}]{status.message}[/{style}]",
        )

    console.print(table)


def _display_failed_sources(statuses: list[SourceAuthStatus]) -> None:
    """Display sources that failed authentication."""
    from rich.console import Console

    console = Console()
    console.print("\n[yellow]Some sources still need configuration:[/yellow]")
    for status in statuses:
        console.print(f"  - [bold]{status.display_name}[/bold]: {status.message}")


def _attempt_auth_for_source(
    status: SourceAuthStatus,
    config: Config,
    auth_manager: AuthManager,
    config_path: str | None,
    checker: PreflightChecker,
    auto_oauth: bool,
) -> SourceAuthStatus:
    """Attempt to authenticate a single source.

    Args:
        status: Source authentication status
        config: Application configuration
        auth_manager: Auth manager instance
        config_path: Path to config file
        checker: Preflight checker instance
        auto_oauth: If True, skip confirmation for OAuth sources

    Returns:
        Updated source authentication status
    """
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
    """Attempt to resolve missing/expired authentication interactively.

    Args:
        statuses: List of source auth statuses
        config: Application configuration
        auth_manager: Auth manager instance
        config_path: Path to config file (needed for OAuth)
        interactive: Whether to prompt for login
        auto_oauth: If True, skip confirmation for OAuth sources (auto-launch browser)

    Returns:
        Updated list of statuses after resolution attempts
    """
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


def _run_preflight_check(
    cfg: Config,
    config_path: str | None,
    non_interactive: bool,
    auto_oauth: bool,
    logger: Any,
) -> None:
    """Run pre-flight authentication check and handle resolution.

    Args:
        cfg: Loaded configuration
        config_path: Path to config file (for OAuth flows)
        non_interactive: If True, fail instead of prompting
        auto_oauth: If True, automatically launch browser OAuth without confirmation
        logger: Logger instance

    Raises:
        SystemExit: If non-interactive and auth is missing, or user declines to proceed
    """
    from rich.console import Console

    console = Console()

    checker = PreflightChecker(preferred_browser=cfg.preferred_browser)
    statuses = checker.check_all_sources(cfg)

    # Display auth status summary
    _display_auth_status(statuses)

    # Handle missing/expired auth
    needs_auth = checker.needs_resolution(statuses)
    if needs_auth:
        if non_interactive:
            console.print(
                "[red]Missing authentication. "
                "Use 'pkm auth login' or remove --non-interactive.[/red]"
            )
            raise SystemExit(1)

        # Auto-prompt login for each source
        auth_manager = _get_auth_manager()
        statuses = _resolve_missing_auth(
            statuses, cfg, auth_manager, config_path, interactive=True, auto_oauth=auto_oauth
        )

    # Check if any still failed
    still_failed = [s for s in statuses if s.state in (AuthState.MISSING, AuthState.INVALID_CONFIG)]
    if still_failed:
        _display_failed_sources(still_failed)
        if not click.confirm("Proceed with available sources?", default=True):
            raise SystemExit(1)


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    Personal Knowledge Management Tool.

    Fetches and formats data from various sources including:
    - Apple Calendar Agenda
    - GitHub
    - Atlassian (Jira/Confluence)
    - Things Logbook
    - Wakatime
    - Google Docs
    - Whoop

    Use subcommands to aggregate all sources or fetch from individual sources:

    \b
    pkm aggregate --date yesterday      Aggregate all sources
    pkm calendar --date yesterday       Fetch Apple Calendar events only
    pkm github --date yesterday         Fetch GitHub activities only
    pkm atlassian --date yesterday      Fetch Atlassian (Jira/Confluence) items only
    pkm things --date yesterday         Fetch Things tasks only
    pkm wakatime --date yesterday       Fetch Wakatime coding activities only
    pkm google-docs --date yesterday    Fetch Google Docs only
    pkm whoop --date yesterday          Fetch Whoop health data only
    pkm server                          Start FastAPI web server
    pkm mcp                             Run as MCP (Model Context Protocol) server
    """
    pass


@cli.command()
@common_options
@click.option("--no-preflight", is_flag=True, help="Skip authentication pre-check")
@click.option("--non-interactive", is_flag=True, help="Fail instead of prompting for auth")
@click.option(
    "--no-auto-oauth",
    is_flag=True,
    default=False,
    help="Disable automatic browser OAuth (ask for confirmation instead)",
)
def aggregate(
    date: str | None,
    from_date: str | None,
    to_date: str | None,
    output_dir: str | None,
    exclude_weekends: bool,
    format: str,
    config: str | None,
    verbose: bool,
    log_format: str,
    no_preflight: bool,
    non_interactive: bool,
    no_auto_oauth: bool,
) -> None:
    """Aggregate data from all configured sources (default behavior)."""
    configure_logging(verbose=verbose, log_format=log_format)
    logger = get_logger(__name__)
    logger.info(
        "pkm_tool_started",
        command="aggregate",
        date_input=date,
        from_date=from_date,
        to_date=to_date,
        exclude_weekends=exclude_weekends,
        output_format=format,
        config_path=config,
        verbose=verbose,
        no_preflight=no_preflight,
        non_interactive=non_interactive,
        no_auto_oauth=no_auto_oauth,
    )

    # Validate date options
    _validate_date_options(date, from_date, to_date, logger)

    # Load config for output settings
    cfg = load_config(config)

    # Pre-flight authentication check (unless skipped)
    if not no_preflight:
        # Auto-OAuth is DEFAULT (True), disabled by --no-auto-oauth flag
        _run_preflight_check(cfg, config, non_interactive, not no_auto_oauth, logger)

    # Check if batch mode (date range) or single-day mode
    if from_date and to_date:
        # Batch mode: generate files for date range
        start_date = _parse_date(from_date, logger)
        end_date = _parse_date(to_date, logger)

        if start_date > end_date:
            logger.error("invalid_date_range", reason="Start date must be <= end date")
            raise click.ClickException("Start date must be before or equal to end date.")

        dates = _generate_date_range(start_date, end_date, exclude_weekends)
        output_directory = Path(output_dir or cfg.output_directory)

        logger.info(
            "batch_mode_started",
            date_count=len(dates),
            output_directory=str(output_directory),
        )

        for target_date in dates:
            try:
                logger.info("fetching_date", date=str(target_date))
                # Only override per-source config if --exclude-weekends was explicitly set (True)
                # False means "use per-source config", not "force include weekends"
                # To force include weekends, set exclude_weekends: false in per-source config
                exclude_override = exclude_weekends if exclude_weekends else None
                data = aggregate_data(
                    target_date, config, exclude_weekends_override=exclude_override
                )

                # Format filename
                filename = format_filename(cfg.output_filename_template, target_date, format)
                output_path = output_directory / filename

                # Write with smart merge
                write_report_to_file(data, output_path, format, merge_existing=True, config=cfg)
                logger.info("report_written", path=str(output_path))
            except Exception as e:
                logger.error(
                    "date_fetch_failed", date=str(target_date), error=str(e), exc_info=True
                )
                click.echo(f"Error processing {target_date}: {e}", err=True)

        click.echo(f"Generated {len(dates)} reports in {output_directory}/")
        logger.info("batch_mode_completed", date_count=len(dates))
    else:
        # Single-day mode: output to stdout
        target_date = _parse_date(date, logger)

        try:
            logger.info("starting_data_aggregation", target_date=str(target_date))
            # Only override per-source config if --exclude-weekends was explicitly set (True)
            # False means "use per-source config", not "force include weekends"
            # To force include weekends, set exclude_weekends: false in per-source config
            exclude_override = exclude_weekends if exclude_weekends else None
            data = aggregate_data(target_date, config, exclude_weekends_override=exclude_override)
            logger.info("data_aggregation_completed", target_date=str(target_date))
        except Exception as e:
            logger.error("data_aggregation_failed", error=str(e), exc_info=True)
            click.echo(f"Error aggregating data: {e}", err=True)
            raise click.Abort()

        _format_and_output(data, format, logger, cfg)


@cli.command()
@common_options
def calendar(
    date: str | None,
    from_date: str | None,
    to_date: str | None,
    output_dir: str | None,
    exclude_weekends: bool,
    format: str,
    config: str | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch Apple Calendar events only."""
    configure_logging(verbose=verbose, log_format=log_format)
    logger = get_logger(__name__)
    logger.info(
        "pkm_tool_started",
        command="calendar",
        date_input=date,
        from_date=from_date,
        to_date=to_date,
        output_format=format,
    )

    cfg = load_config(config)
    _process_batch_or_single(
        "apple_calendar",
        fetch_calendar_events,
        date,
        from_date,
        to_date,
        output_dir,
        exclude_weekends,
        format,
        config,
        cfg.apple_calendar.config,
        logger,
    )


@cli.command()
@common_options
def github(
    date: str | None,
    from_date: str | None,
    to_date: str | None,
    output_dir: str | None,
    exclude_weekends: bool,
    format: str,
    config: str | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch GitHub activities only."""
    configure_logging(verbose=verbose, log_format=log_format)
    logger = get_logger(__name__)
    logger.info(
        "pkm_tool_started",
        command="github",
        date_input=date,
        from_date=from_date,
        to_date=to_date,
        output_format=format,
    )

    cfg = load_config(config)
    _process_batch_or_single(
        "github",
        fetch_github_activities,
        date,
        from_date,
        to_date,
        output_dir,
        exclude_weekends,
        format,
        config,
        cfg.github.config,
        logger,
    )


@cli.command()
@common_options
def atlassian(
    date: str | None,
    from_date: str | None,
    to_date: str | None,
    output_dir: str | None,
    exclude_weekends: bool,
    format: str,
    config: str | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch Atlassian (Jira/Confluence) items only."""
    configure_logging(verbose=verbose, log_format=log_format)
    logger = get_logger(__name__)
    logger.info(
        "pkm_tool_started",
        command="atlassian",
        date_input=date,
        from_date=from_date,
        to_date=to_date,
        output_format=format,
    )

    cfg = load_config(config)
    _process_batch_or_single(
        "atlassian",
        fetch_atlassian_items,
        date,
        from_date,
        to_date,
        output_dir,
        exclude_weekends,
        format,
        config,
        cfg.atlassian.config,
        logger,
    )


@cli.command()
@common_options
def things(
    date: str | None,
    from_date: str | None,
    to_date: str | None,
    output_dir: str | None,
    exclude_weekends: bool,
    format: str,
    config: str | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch Things tasks only."""
    configure_logging(verbose=verbose, log_format=log_format)
    logger = get_logger(__name__)
    logger.info(
        "pkm_tool_started",
        command="things",
        date_input=date,
        from_date=from_date,
        to_date=to_date,
        output_format=format,
    )

    cfg = load_config(config)
    _process_batch_or_single(
        "things",
        fetch_things_tasks,
        date,
        from_date,
        to_date,
        output_dir,
        exclude_weekends,
        format,
        config,
        cfg.things.config,
        logger,
    )


@cli.command()
@common_options
def wakatime(
    date: str | None,
    from_date: str | None,
    to_date: str | None,
    output_dir: str | None,
    exclude_weekends: bool,
    format: str,
    config: str | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch Wakatime coding activities only."""
    configure_logging(verbose=verbose, log_format=log_format)
    logger = get_logger(__name__)
    logger.info(
        "pkm_tool_started",
        command="wakatime",
        date_input=date,
        from_date=from_date,
        to_date=to_date,
        output_format=format,
    )

    cfg = load_config(config)
    _process_batch_or_single(
        "wakatime",
        fetch_wakatime_activities,
        date,
        from_date,
        to_date,
        output_dir,
        exclude_weekends,
        format,
        config,
        cfg.wakatime.config,
        logger,
    )


@cli.group()
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


@cli.command(name="google-docs")
@common_options
def google_docs(
    date: str | None,
    from_date: str | None,
    to_date: str | None,
    output_dir: str | None,
    exclude_weekends: bool,
    format: str,
    config: str | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch Google Docs only."""
    configure_logging(verbose=verbose, log_format=log_format)
    logger = get_logger(__name__)
    logger.info(
        "pkm_tool_started",
        command="google-docs",
        date_input=date,
        from_date=from_date,
        to_date=to_date,
        output_format=format,
    )

    cfg = load_config(config)
    _process_batch_or_single(
        "google_docs",
        fetch_google_docs,
        date,
        from_date,
        to_date,
        output_dir,
        exclude_weekends,
        format,
        config,
        cfg.google_docs.config,
        logger,
    )


@cli.command()
@common_options
def whoop(
    date: str | None,
    from_date: str | None,
    to_date: str | None,
    output_dir: str | None,
    exclude_weekends: bool,
    format: str,
    config: str | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch Whoop health data only."""
    configure_logging(verbose=verbose, log_format=log_format)
    logger = get_logger(__name__)
    logger.info(
        "pkm_tool_started",
        command="whoop",
        date_input=date,
        from_date=from_date,
        to_date=to_date,
        output_format=format,
    )

    # Validate date options
    _validate_date_options(date, from_date, to_date, logger)

    # Load config for output settings
    cfg = load_config(config)

    def fetch_whoop_data(target_dt: dt.date, whoop_config: dict[str, Any]) -> tuple:
        """Wrapper to fetch all three types of Whoop data."""
        recovery = fetch_whoop_recovery(target_dt, whoop_config)
        sleep = fetch_whoop_sleep(target_dt, whoop_config)
        workouts = fetch_whoop_workouts(target_dt, whoop_config)
        return (recovery, sleep, workouts)

    # Check if batch mode (date range) or single-day mode
    if from_date and to_date:
        # Batch mode: generate files for date range
        start_date = _parse_date(from_date, logger)
        end_date = _parse_date(to_date, logger)

        if start_date > end_date:
            logger.error("invalid_date_range", reason="Start date must be <= end date")
            raise click.ClickException("Start date must be before or equal to end date.")

        dates = _generate_date_range(start_date, end_date, exclude_weekends)
        output_directory = Path(output_dir or cfg.output_directory)

        logger.info(
            "batch_mode_started",
            source="whoop",
            date_count=len(dates),
            output_directory=str(output_directory),
        )

        for target_date in dates:
            try:
                logger.info("fetching_date", source="whoop", date=str(target_date))

                # Create AggregatedData and populate Whoop fields
                data = AggregatedData(date=target_date)
                data.whoop_recovery, data.whoop_sleep, data.whoop_workouts = fetch_whoop_data(
                    target_date, cfg.whoop.config
                )

                # Format filename
                filename = format_filename(cfg.output_filename_template, target_date, format)
                output_path = output_directory / filename

                # Write with smart merge
                write_report_to_file(data, output_path, format, merge_existing=True, config=cfg)
                logger.info("report_written", path=str(output_path))
            except Exception as e:
                logger.error(
                    "date_fetch_failed", date=str(target_date), error=str(e), exc_info=True
                )
                click.echo(f"Error processing {target_date}: {e}", err=True)

        click.echo(f"Generated {len(dates)} reports in {output_directory}/")
        logger.info("batch_mode_completed", source="whoop", date_count=len(dates))
    else:
        # Single-day mode: output to stdout
        target_date = _parse_date(date, logger)

        # Create AggregatedData and populate Whoop fields
        data = AggregatedData(date=target_date)

        logger.info("fetching_source", source="whoop")
        start_time = time.time()
        try:
            # Fetch all three types of Whoop data
            data.whoop_recovery = fetch_whoop_recovery(target_date, cfg.whoop.config)
            data.whoop_sleep = fetch_whoop_sleep(target_date, cfg.whoop.config)
            data.whoop_workouts = fetch_whoop_workouts(target_date, cfg.whoop.config)

            recovery_count = 1 if data.whoop_recovery else 0
            total_items = recovery_count + len(data.whoop_sleep) + len(data.whoop_workouts)
            duration = time.time() - start_time

            logger.info(
                "source_fetch_completed",
                source="whoop",
                duration_seconds=f"{duration:.2f}",
                items_count=total_items,
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "source_fetch_failed",
                source="whoop",
                error=str(e),
                duration_seconds=f"{duration:.2f}",
                exc_info=True,
            )
            click.echo(f"Error fetching whoop: {e}", err=True)
            raise click.Abort()

        _format_and_output(data, format, logger, cfg)


@cli.command("preflight")
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to config file")
def preflight_cmd(config: str | None) -> None:
    """Check authentication status for all data sources."""
    from rich.console import Console

    console = Console()
    cfg = load_config(config)

    checker = PreflightChecker(preferred_browser=cfg.preferred_browser)
    statuses = checker.check_all_sources(cfg)

    # Display status table
    _display_auth_status(statuses)

    # Summary
    summary = checker.get_summary(statuses)
    valid = summary.get("valid", 0) + summary.get("not_required", 0)
    missing = summary.get("missing", 0) + summary.get("expired", 0)
    disabled = summary.get("disabled", 0)

    console.print()
    if missing > 0:
        console.print(f"[yellow]{valid} sources ready, {missing} need authentication[/yellow]")
        console.print("\nRun [bold]pkm auth login <source>[/bold] to authenticate.")
    else:
        console.print(f"[green]All {valid} sources ready![/green]")

    if disabled > 0:
        console.print(f"[dim]({disabled} sources disabled)[/dim]")


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default=None,
    help="Path to configuration file",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose (DEBUG) logging",
)
@click.option(
    "--log-format",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    help="Log output format (default: human)",
)
def mcp(
    config: str | None,
    verbose: bool,
    log_format: str,
) -> None:
    """
    Run PKM Tool as an MCP (Model Context Protocol) server.

    The MCP server exposes PKM Tool's data fetching capabilities as tools
    that can be used by AI assistants supporting the MCP protocol.

    Communication is via stdio (standard input/output), making it compatible
    with MCP clients like Claude Desktop.

    Available tools:
    - fetch_aggregated_data: Get data from all configured sources
    - fetch_calendar_events: Get Apple Calendar events
    - fetch_github_activities: Get GitHub activities
    - fetch_atlassian_items: Get Atlassian (Jira/Confluence) items
    - fetch_things_tasks: Get Things tasks
    - fetch_wakatime_activities: Get Wakatime coding activities
    - fetch_google_docs: Get Google Docs
    - fetch_whoop_data: Get Whoop health data

    Example configuration for Claude Desktop:
    (~/Library/Application Support/Claude/claude_desktop_config.json)

    \b
    {
      "mcpServers": {
        "pkm-tool": {
          "command": "pkm",
          "args": ["mcp"],
          "env": {}
        }
      }
    }
    """
    # Configure logging
    configure_logging(verbose=verbose, log_format=log_format)
    logger = get_logger(__name__)

    logger.info("starting_mcp_server", config_path=config)

    try:
        import asyncio

        from pkm_tool.mcp_server import run_mcp_server

        # Run the MCP server with config path
        asyncio.run(run_mcp_server(config))
    except ImportError:
        logger.error("mcp_dependencies_missing")
        click.echo(
            "Error: MCP dependencies not installed. Install with: uv sync --extra mcp",
            err=True,
        )
        raise click.Abort()
    except Exception as e:
        logger.error("mcp_server_failed", error=str(e), exc_info=True)
        click.echo(f"Error running MCP server: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind the server to (default: 127.0.0.1)",
)
@click.option(
    "--port",
    default=8000,
    type=int,
    help="Port to bind the server to (default: 8000)",
)
@click.option(
    "--reload",
    is_flag=True,
    default=False,
    help="Enable auto-reload on code changes (development mode)",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default=None,
    help="Path to configuration file",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose (DEBUG) logging",
)
@click.option(
    "--log-format",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    help="Log output format (default: human)",
)
def server(
    host: str,
    port: int,
    reload: bool,
    config: str | None,
    verbose: bool,
    log_format: str,
) -> None:
    """
    Start the PKM Tool web server.

    Runs a FastAPI server that provides:
    - REST API endpoints for fetching data
    - Interactive API documentation at /docs

    Examples:

    \b
    # Start server on default port (8000)
    pkm server

    \b
    # Start on custom port with auto-reload
    pkm server --port 8080 --reload

    \b
    # Start with verbose logging
    pkm server --verbose

    The server will be accessible at http://{host}:{port}
    API documentation will be available at http://{host}:{port}/docs
    """
    # Configure logging
    configure_logging(verbose=verbose, log_format=log_format)
    logger = get_logger(__name__)

    logger.info("starting_server", host=host, port=port, reload=reload)

    try:
        import uvicorn

        from pkm_tool.server.api import app

        # Display helpful information
        click.echo(f"🚀 Starting PKM Tool server on http://{host}:{port}")
        click.echo(f"📚 API documentation: http://{host}:{port}/docs")
        click.echo(f"📖 ReDoc documentation: http://{host}:{port}/redoc")
        click.echo()
        click.echo("Press CTRL+C to stop the server")
        click.echo()

        # Run the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level="debug" if verbose else "info",
        )
    except ImportError:
        logger.error("server_dependencies_missing")
        click.echo(
            "Error: Server dependencies not installed. Install with: uv sync --extra server",
            err=True,
        )
        raise click.Abort()
    except Exception as e:
        logger.error("server_start_failed", error=str(e), exc_info=True)
        click.echo(f"Error starting server: {e}", err=True)
        raise click.Abort()


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
