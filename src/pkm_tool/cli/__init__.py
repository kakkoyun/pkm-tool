"""CLI entry point for PKM tool.

This package decomposes the CLI into focused modules:
- common.py:    Shared options, helpers, constants
- auth.py:      Authentication subcommands
- sources.py:   Individual data source subcommands
- preflight.py: Pre-flight authentication checks
- servers.py:   MCP and REST API server commands
"""

from pathlib import Path

import click

from pkm_tool.aggregator import aggregate_data
from pkm_tool.config import load_config
from pkm_tool.formatters import format_filename, write_report_to_file
from pkm_tool.logging import bind_correlation_id, configure_logging, get_logger

from .auth import auth
from .common import (
    _AUTH_MANAGER as _AUTH_MANAGER,
)
from .common import (
    _format_and_output,
    _generate_date_range,
    _parse_date_for_cli,
    _validate_date_options,
    common_options,
)
from .preflight import _run_preflight_check, preflight_cmd
from .servers import mcp, server
from .sources import (
    atlassian,
    calendar,
    github,
    google_docs,
    things,
    wakatime,
    whoop,
)


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
    bind_correlation_id()
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
        start_date = _parse_date_for_cli(from_date, logger)
        end_date = _parse_date_for_cli(to_date, logger)

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
        target_date = _parse_date_for_cli(date, logger)

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


# Register all subcommands on the cli group
cli.add_command(auth)
cli.add_command(calendar)
cli.add_command(github)
cli.add_command(atlassian)
cli.add_command(things)
cli.add_command(wakatime)
cli.add_command(google_docs)
cli.add_command(whoop)
cli.add_command(preflight_cmd)
cli.add_command(mcp)
cli.add_command(server)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
