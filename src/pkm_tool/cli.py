"""CLI entry point for PKM tool."""

import functools
import json
import time
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

import click
from dateutil import parser as date_parser

from pkm_tool.aggregator import aggregate_data
from pkm_tool.auth import AuthManager
from pkm_tool.auth.oauth import GoogleOAuthProvider
from pkm_tool.config import load_config
from pkm_tool.formatters import format_as_json, format_as_markdown
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
    return GoogleOAuthProvider(client_id, client_secret=client_secret, scopes=scopes)


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


def _parse_date(date_input: str | None, logger: Any) -> date:
    """
    Parse date string into date object.

    Args:
        date_input: Date string (YYYY-MM-DD or natural language) or None for today
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

    try:
        parsed_date = date_parser.parse(date_input)
        target_date = parsed_date.date()
        logger.debug("parsed_date", input=date_input, parsed=str(target_date))
        return target_date
    except (ValueError, TypeError) as e:
        logger.error("date_parsing_failed", error=str(e), input=date_input)
        click.echo(f"Error parsing date: {e}", err=True)
        raise click.Abort()


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


def _format_and_output(data: AggregatedData, format: str, logger: Any) -> None:
    """
    Format data and output to stdout.

    Args:
        data: AggregatedData to format
        format: Output format (markdown or json)
        logger: Logger instance
    """
    logger.debug("formatting_output", format=format)
    if format.lower() == "json":
        output = format_as_json(data)
    else:
        output = format_as_markdown(data)
    click.echo(output)
    logger.info("pkm_tool_completed", output_format=format)


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "--date",
    "-d",
    default=None,
    help="Date to fetch data for (default: today). Format: YYYY-MM-DD or natural language.",
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
def cli(
    ctx: click.Context,
    date: str | None,
    format: str,
    config: str | None,
    verbose: bool,
    log_format: str,
) -> None:
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

    Run without subcommand to aggregate all sources, or use subcommands
    to fetch from individual sources:

    \b
    pkm --date yesterday                Aggregate all sources (backward compat)
    pkm aggregate --date yesterday      Explicitly aggregate all sources
    pkm calendar --date yesterday       Fetch Apple Calendar events only
    pkm github --date yesterday         Fetch GitHub activities only
    pkm atlassian --date yesterday      Fetch Atlassian (Jira/Confluence) items only
    pkm things --date yesterday         Fetch Things tasks only
    pkm wakatime --date yesterday       Fetch Wakatime coding activities only
    pkm google-docs --date yesterday    Fetch Google Docs only
    pkm whoop --date yesterday          Fetch Whoop health data only
    """
    # Backward compatibility: if no subcommand specified, run aggregate with group options
    if ctx.invoked_subcommand is None:
        ctx.invoke(
            aggregate,
            date=date,
            format=format,
            config=config,
            verbose=verbose,
            log_format=log_format,
        )


@cli.command()
@common_options
def aggregate(
    date: str | None,
    format: str,
    config: str | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Aggregate data from all configured sources (default behavior)."""
    configure_logging(verbose=verbose, log_format=log_format)
    logger = get_logger(__name__)
    logger.info(
        "pkm_tool_started",
        command="aggregate",
        date_input=date,
        output_format=format,
        config_path=config,
        verbose=verbose,
    )

    target_date = _parse_date(date, logger)

    try:
        logger.info("starting_data_aggregation", target_date=str(target_date))
        data = aggregate_data(target_date, config)
        logger.info("data_aggregation_completed", target_date=str(target_date))
    except Exception as e:
        logger.error("data_aggregation_failed", error=str(e), exc_info=True)
        click.echo(f"Error aggregating data: {e}", err=True)
        raise click.Abort()

    _format_and_output(data, format, logger)


@cli.command()
@common_options
def calendar(
    date: str | None,
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
        output_format=format,
    )

    target_date = _parse_date(date, logger)
    cfg = load_config(config)

    data = _fetch_single_source(
        "apple_calendar",
        fetch_calendar_events,
        target_date,
        cfg.apple_calendar.config,
        logger,
    )
    _format_and_output(data, format, logger)


@cli.command()
@common_options
def github(
    date: str | None,
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
        output_format=format,
    )

    target_date = _parse_date(date, logger)
    cfg = load_config(config)

    data = _fetch_single_source(
        "github",
        fetch_github_activities,
        target_date,
        cfg.github.config,
        logger,
    )
    _format_and_output(data, format, logger)


@cli.command()
@common_options
def atlassian(
    date: str | None,
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
        output_format=format,
    )

    target_date = _parse_date(date, logger)
    cfg = load_config(config)

    data = _fetch_single_source(
        "atlassian",
        fetch_atlassian_items,
        target_date,
        cfg.atlassian.config,
        logger,
    )
    _format_and_output(data, format, logger)


@cli.command()
@common_options
def things(
    date: str | None,
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
        output_format=format,
    )

    target_date = _parse_date(date, logger)
    cfg = load_config(config)

    data = _fetch_single_source(
        "things",
        fetch_things_tasks,
        target_date,
        cfg.things.config,
        logger,
    )
    _format_and_output(data, format, logger)


@cli.command()
@common_options
def wakatime(
    date: str | None,
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
        output_format=format,
    )

    target_date = _parse_date(date, logger)
    cfg = load_config(config)

    data = _fetch_single_source(
        "wakatime",
        fetch_wakatime_activities,
        target_date,
        cfg.wakatime.config,
        logger,
    )
    _format_and_output(data, format, logger)


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
        base_url = click.prompt(
            "Atlassian base URL", default=atlas_cfg.get("base_url", "https://example.atlassian.net")
        )
        username = click.prompt(
            "Atlassian email", default=atlas_cfg.get("username", "user@example.com")
        )
        api_token = click.prompt("Atlassian API token", hide_input=True)
        payload = json.dumps({"base_url": base_url, "username": username, "api_token": api_token})
        manager.store_api_token(store_key, payload, token_type="atlassian_json")
        click.echo("Stored Atlassian credentials securely.")
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
        output_format=format,
    )

    target_date = _parse_date(date, logger)
    cfg = load_config(config)

    data = _fetch_single_source(
        "google_docs",
        fetch_google_docs,
        target_date,
        cfg.google_docs.config,
        logger,
    )
    _format_and_output(data, format, logger)


@cli.command()
@common_options
def whoop(
    date: str | None,
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
        output_format=format,
    )

    target_date = _parse_date(date, logger)
    cfg = load_config(config)

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

    _format_and_output(data, format, logger)


# Keep main() as entry point for backward compatibility
def main() -> None:
    """Entry point wrapper for backward compatibility."""
    cli()


if __name__ == "__main__":
    main()
