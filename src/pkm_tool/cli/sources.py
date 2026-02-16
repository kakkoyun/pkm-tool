"""Individual data source CLI subcommands."""

import datetime as dt
import time
from pathlib import Path
from typing import Any

import click

from pkm_tool.config import load_config
from pkm_tool.formatters import format_filename, write_report_to_file
from pkm_tool.logging import bind_correlation_id, configure_logging, get_logger
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

from .common import (
    _format_and_output,
    _generate_date_range,
    _parse_date_for_cli,
    _process_batch_or_single,
    _validate_date_options,
    common_options,
)


@click.command()
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
    bind_correlation_id()
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


@click.command()
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
    bind_correlation_id()
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


@click.command()
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


@click.command()
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


@click.command()
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


@click.command(name="google-docs")
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


@click.command()
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
        start_date = _parse_date_for_cli(from_date, logger)
        end_date = _parse_date_for_cli(to_date, logger)

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
        target_date = _parse_date_for_cli(date, logger)

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
