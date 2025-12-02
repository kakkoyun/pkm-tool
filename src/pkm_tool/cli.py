"""CLI entry point for PKM tool."""

import datetime as dt
import functools
import json
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import click
from dateutil import parser as date_parser

from pkm_tool.aggregator import aggregate_data
from pkm_tool.auth import AuthManager
from pkm_tool.auth.oauth import GoogleOAuthProvider
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


@click.group(invoke_without_command=True)
@click.pass_context
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
def cli(
    ctx: click.Context,
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
            from_date=from_date,
            to_date=to_date,
            output_dir=output_dir,
            exclude_weekends=exclude_weekends,
            format=format,
            config=config,
            verbose=verbose,
            log_format=log_format,
        )


@cli.command()
@common_options
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
    )

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


# Keep main() as entry point for backward compatibility
def main() -> None:
    """Entry point wrapper for backward compatibility."""
    cli()


if __name__ == "__main__":
    main()
