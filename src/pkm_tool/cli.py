"""CLI entry point for PKM tool."""

import functools
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

import click
from dateutil import parser as date_parser

from pkm_tool.aggregator import aggregate_data
from pkm_tool.config import Config, load_config
from pkm_tool.formatters import (
    format_as_json,
    format_as_markdown,
    format_reports_as_json,
    format_reports_as_markdown,
)
from pkm_tool.logging import configure_logging, get_logger
from pkm_tool.models import AggregatedData


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
        "--start-date",
        default=None,
        help="Start date for range (inclusive). Format: YYYY-MM-DD or natural language.",
    )
    @click.option(
        "--end-date",
        default=None,
        help="End date for range (inclusive). Format: YYYY-MM-DD or natural language.",
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
        "--exclude-weekends/--include-weekends",
        default=None,
        help="Exclude (or include) weekend dates for all sources (overrides config).",
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


def _resolve_date_range(
    date_input: str | None,
    start_date_input: str | None,
    end_date_input: str | None,
    logger: Any,
) -> tuple[date, date]:
    """
    Resolve date inputs into concrete start/end dates.

    Args:
        date_input: Single date provided via --date
        start_date_input: Range start provided via --start-date
        end_date_input: Range end provided via --end-date
        logger: Logger instance

    Returns:
        Tuple of (start_date, end_date)
    """
    if date_input and (start_date_input or end_date_input):
        logger.error("date_input_conflict", date=date_input, start=start_date_input, end=end_date_input)
        click.echo("Cannot combine --date with --start-date/--end-date.", err=True)
        raise click.Abort()

    if (start_date_input and not end_date_input) or (end_date_input and not start_date_input):
        logger.error("date_range_incomplete", start=start_date_input, end=end_date_input)
        click.echo("Both --start-date and --end-date must be provided for ranges.", err=True)
        raise click.Abort()

    if start_date_input and end_date_input:
        start_date = _parse_date(start_date_input, logger)
        end_date = _parse_date(end_date_input, logger)
    else:
        # Fall back to single date (explicit or implicit today)
        single_date = _parse_date(date_input, logger)
        return single_date, single_date

    if end_date < start_date:
        logger.error("date_range_invalid", start=str(start_date), end=str(end_date))
        click.echo("--end-date must be on or after --start-date.", err=True)
        raise click.Abort()

    logger.debug(
        "resolved_date_range",
        start=str(start_date),
        end=str(end_date),
    )
    return start_date, end_date


def _generate_date_range(
    start_date: date,
    end_date: date,
    exclude_weekends: bool,
) -> list[date]:
    """
    Generate a list of dates between start and end (inclusive).

    Args:
        start_date: First date in range
        end_date: Last date in range
        exclude_weekends: Whether to skip weekend dates entirely

    Returns:
        List of dates in ascending order
    """
    dates: list[date] = []
    current = start_date
    while current <= end_date:
        if not exclude_weekends or current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)

    return dates


SOURCE_FIELDS: tuple[str, ...] = (
    "apple_calendar",
    "github",
    "atlassian",
    "things",
    "wakatime",
    "google_docs",
    "whoop",
)


def _build_single_source_config(base_config: Config, source_field: str) -> Config:
    """
    Create a config copy that enables only the requested source.

    WHY: Single-source commands should fetch their target regardless of the
    global enablement flags, while ensuring other sources remain disabled.
    """
    config_copy = base_config.model_copy(deep=True)
    for field in SOURCE_FIELDS:
        source_cfg = getattr(config_copy, field)
        source_cfg.enabled = field == source_field
    return config_copy


def _resolve_dates_for_command(
    date_input: str | None,
    start_date_input: str | None,
    end_date_input: str | None,
    config: Config,
    exclude_weekends_flag: bool | None,
    logger: Any,
) -> tuple[list[date], tuple[date, date], bool]:
    """Resolve CLI date inputs and apply optional weekend filtering."""
    start, end = _resolve_date_range(date_input, start_date_input, end_date_input, logger)
    weekend_filter = exclude_weekends_flag if exclude_weekends_flag is not None else config.exclude_weekends
    dates = _generate_date_range(start, end, weekend_filter)
    logger.debug(
        "date_range_ready",
        start=str(start),
        end=str(end),
        exclude_weekends=weekend_filter,
        days=len(dates),
    )
    return dates, (start, end), weekend_filter


def _collect_reports_for_dates(
    dates: list[date],
    config_path: str | None,
    config_obj: Config,
    logger: Any,
    exclude_weekends_override: bool | None,
) -> list[AggregatedData]:
    """Fetch AggregatedData for each requested date."""
    reports: list[AggregatedData] = []
    for current_date in dates:
        try:
            logger.info("starting_data_aggregation", target_date=str(current_date))
            report = aggregate_data(
                current_date,
                config_path,
                exclude_weekends_override=exclude_weekends_override,
                config_obj=config_obj,
            )
            logger.info("data_aggregation_completed", target_date=str(current_date))
            reports.append(report)
        except Exception as e:
            logger.error(
                "data_aggregation_failed",
                target_date=str(current_date),
                error=str(e),
                exc_info=True,
            )
            click.echo(f"Error aggregating data for {current_date}: {e}", err=True)
            raise click.Abort()
    return reports


def _run_single_source_command(
    command_name: str,
    source_field: str,
    date: str | None,
    start_date: str | None,
    end_date: str | None,
    format: str,
    config: str | None,
    exclude_weekends: bool | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Shared execution path for single-source CLI commands."""
    configure_logging(verbose=verbose, log_format=log_format)
    logger = get_logger(__name__)
    logger.info(
        "pkm_tool_started",
        command=command_name,
        date_input=date,
        start_date_input=start_date,
        end_date_input=end_date,
        output_format=format,
        config_path=config,
        exclude_weekends_flag=exclude_weekends,
        verbose=verbose,
    )

    cfg = load_config(config)
    dates, resolved_range, weekend_filter = _resolve_dates_for_command(
        date, start_date, end_date, cfg, exclude_weekends, logger
    )

    if not dates:
        logger.info(
            "no_dates_to_process",
            command=command_name,
            start=str(resolved_range[0]),
            end=str(resolved_range[1]),
            exclude_weekends=weekend_filter,
        )
        click.echo("No dates to process after applying weekend filtering.", err=True)
        raise click.Abort()

    single_config = _build_single_source_config(cfg, source_field)
    reports = _collect_reports_for_dates(dates, config, single_config, logger, exclude_weekends)
    _format_and_output(reports, format, logger, date_range=resolved_range)


def _format_and_output(
    data: AggregatedData | list[AggregatedData],
    format: str,
    logger: Any,
    date_range: tuple[date, date] | None = None,
) -> None:
    """
    Format data and output to stdout.

    Args:
        data: AggregatedData or list of AggregatedData to format
        format: Output format (markdown or json)
        logger: Logger instance
        date_range: Optional (start, end) tuple for multi-day summaries
    """
    if isinstance(data, list):
        logger.debug("formatting_output", format=format, reports=len(data))
        if not data:
            logger.warning("no_reports_to_format")
            click.echo("No data available for the requested dates.", err=True)
            return
        if format.lower() == "json":
            output = format_reports_as_json(data, date_range)
        else:
            output = format_reports_as_markdown(data, date_range)
    else:
        logger.debug("formatting_output", format=format, reports=1)
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
    "--start-date",
    default=None,
    help="Start date for range (inclusive). Format: YYYY-MM-DD or natural language.",
)
@click.option(
    "--end-date",
    default=None,
    help="End date for range (inclusive). Format: YYYY-MM-DD or natural language.",
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
    "--exclude-weekends/--include-weekends",
    default=None,
    help="Exclude (or include) weekend dates for all sources (overrides config).",
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
    start_date: str | None,
    end_date: str | None,
    format: str,
    config: str | None,
    exclude_weekends: bool | None,
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
            start_date=start_date,
            end_date=end_date,
            format=format,
            config=config,
            exclude_weekends=exclude_weekends,
            verbose=verbose,
            log_format=log_format,
        )


@cli.command()
@common_options
def aggregate(
    date: str | None,
    start_date: str | None,
    end_date: str | None,
    format: str,
    config: str | None,
    exclude_weekends: bool | None,
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
        start_date_input=start_date,
        end_date_input=end_date,
        output_format=format,
        config_path=config,
        exclude_weekends_flag=exclude_weekends,
        verbose=verbose,
    )

    cfg = load_config(config)
    dates, resolved_range, weekend_filter = _resolve_dates_for_command(
        date, start_date, end_date, cfg, exclude_weekends, logger
    )

    if not dates:
        logger.info(
            "no_dates_to_process",
            start=str(resolved_range[0]),
            end=str(resolved_range[1]),
            exclude_weekends=weekend_filter,
        )
        click.echo("No dates to process after applying weekend filtering.", err=True)
        raise click.Abort()

    reports = _collect_reports_for_dates(dates, config, cfg, logger, exclude_weekends)
    _format_and_output(reports, format, logger, date_range=resolved_range)


@cli.command()
@common_options
def calendar(
    date: str | None,
    start_date: str | None,
    end_date: str | None,
    format: str,
    config: str | None,
    exclude_weekends: bool | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch Apple Calendar events only."""
    _run_single_source_command(
        "calendar",
        "apple_calendar",
        date,
        start_date,
        end_date,
        format,
        config,
        exclude_weekends,
        verbose,
        log_format,
    )


@cli.command()
@common_options
def github(
    date: str | None,
    start_date: str | None,
    end_date: str | None,
    format: str,
    config: str | None,
    exclude_weekends: bool | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch GitHub activities only."""
    _run_single_source_command(
        "github",
        "github",
        date,
        start_date,
        end_date,
        format,
        config,
        exclude_weekends,
        verbose,
        log_format,
    )


@cli.command()
@common_options
def atlassian(
    date: str | None,
    start_date: str | None,
    end_date: str | None,
    format: str,
    config: str | None,
    exclude_weekends: bool | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch Atlassian (Jira/Confluence) items only."""
    _run_single_source_command(
        "atlassian",
        "atlassian",
        date,
        start_date,
        end_date,
        format,
        config,
        exclude_weekends,
        verbose,
        log_format,
    )


@cli.command()
@common_options
def things(
    date: str | None,
    start_date: str | None,
    end_date: str | None,
    format: str,
    config: str | None,
    exclude_weekends: bool | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch Things tasks only."""
    _run_single_source_command(
        "things",
        "things",
        date,
        start_date,
        end_date,
        format,
        config,
        exclude_weekends,
        verbose,
        log_format,
    )


@cli.command()
@common_options
def wakatime(
    date: str | None,
    start_date: str | None,
    end_date: str | None,
    format: str,
    config: str | None,
    exclude_weekends: bool | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch Wakatime coding activities only."""
    _run_single_source_command(
        "wakatime",
        "wakatime",
        date,
        start_date,
        end_date,
        format,
        config,
        exclude_weekends,
        verbose,
        log_format,
    )


@cli.command(name="google-docs")
@common_options
def google_docs(
    date: str | None,
    start_date: str | None,
    end_date: str | None,
    format: str,
    config: str | None,
    exclude_weekends: bool | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch Google Docs only."""
    _run_single_source_command(
        "google-docs",
        "google_docs",
        date,
        start_date,
        end_date,
        format,
        config,
        exclude_weekends,
        verbose,
        log_format,
    )


@cli.command()
@common_options
def whoop(
    date: str | None,
    start_date: str | None,
    end_date: str | None,
    format: str,
    config: str | None,
    exclude_weekends: bool | None,
    verbose: bool,
    log_format: str,
) -> None:
    """Fetch Whoop health data only."""
    _run_single_source_command(
        "whoop",
        "whoop",
        date,
        start_date,
        end_date,
        format,
        config,
        exclude_weekends,
        verbose,
        log_format,
    )


# Keep main() as entry point for backward compatibility
def main() -> None:
    """Entry point wrapper for backward compatibility."""
    cli()


if __name__ == "__main__":
    main()
