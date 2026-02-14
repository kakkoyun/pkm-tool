"""Shared CLI options, helpers, and constants."""

import datetime as dt
import functools
import time
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

if TYPE_CHECKING:
    from pkm_tool.auth.oauth.atlassian import AtlassianOAuthProvider

from pkm_tool.auth import AuthManager
from pkm_tool.auth.oauth import GoogleOAuthProvider
from pkm_tool.config import Config, load_config
from pkm_tool.dates import parse_date
from pkm_tool.formatters import (
    format_as_json,
    format_as_markdown,
    format_filename,
    write_report_to_file,
)
from pkm_tool.models import AggregatedData

# Maps source name → AggregatedData field name for single-field sources.
# Whoop is excluded because it populates three fields from a tuple result.
_SOURCE_FIELD_MAP: dict[str, str] = {
    "apple_calendar": "calendar_events",
    "github": "github_activities",
    "atlassian": "atlassian_items",
    "things": "things_tasks",
    "wakatime": "wakatime_activities",
    "google_docs": "google_docs",
}


def _populate_source_data(data: AggregatedData, source_name: str, result: Any) -> None:
    """Set the appropriate field on AggregatedData for a given source result."""
    field = _SOURCE_FIELD_MAP.get(source_name)
    if field:
        setattr(data, field, result)
    elif source_name == "whoop":
        data.whoop_recovery, data.whoop_sleep, data.whoop_workouts = result


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


def _format_expiry(timestamp: dt.datetime | None) -> str:
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


def _parse_date_for_cli(date_input: str | None, logger: Any) -> date:
    """Parse date string, raising click.Abort on failure."""
    try:
        target_date = parse_date(date_input)
        logger.debug("parsed_date", input=date_input, parsed=str(target_date))
        return target_date
    except ValueError as e:
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

        _populate_source_data(data, source_name, result)

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
        start_date = _parse_date_for_cli(from_date, logger)
        end_date = _parse_date_for_cli(to_date, logger)

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

                _populate_source_data(data, source_name, result)

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
        target_date = _parse_date_for_cli(date, logger)
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
