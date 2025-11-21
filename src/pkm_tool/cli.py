"""CLI entry point for PKM tool."""

import functools
import time
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

import click
from dateutil import parser as date_parser

from pkm_tool.aggregator import aggregate_data
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

    # Fetch all Whoop data types
    def fetch_all_whoop_data(target_date: date, config: dict[str, Any]) -> tuple:
        """Fetch recovery, sleep, and workouts."""
        recovery = fetch_whoop_recovery(target_date, config)
        sleep = fetch_whoop_sleep(target_date, config)
        workouts = fetch_whoop_workouts(target_date, config)
        return (recovery, sleep, workouts)

    data = _fetch_single_source(
        "whoop",
        fetch_all_whoop_data,
        target_date,
        cfg.whoop.config,
        logger,
    )
    _format_and_output(data, format, logger)


# Keep main() as entry point for backward compatibility
def main() -> None:
    """Entry point wrapper for backward compatibility."""
    cli()


if __name__ == "__main__":
    main()
