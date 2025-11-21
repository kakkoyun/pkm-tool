"""CLI entry point for PKM tool."""

from datetime import datetime

import click
from dateutil import parser as date_parser

from pkm_tool.aggregator import aggregate_data
from pkm_tool.formatters import format_as_json, format_as_markdown
from pkm_tool.logging import configure_logging, get_logger


@click.command(name="pkm")
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
def main(date: str | None, format: str, config: str | None, verbose: bool, log_format: str) -> None:
    """
    Personal Knowledge Management Tool.

    Fetches and formats data from various sources including:
    - Apple Calendar Agenda
    - GitHub
    - Atlassian (Jira/Confluence)
    - Things Logbook
    - Wakatime
    - Google Docs
    """
    # Initialize logging
    configure_logging(verbose=verbose, log_format=log_format)
    logger = get_logger(__name__)

    logger.info(
        "pkm_tool_started",
        date_input=date,
        output_format=format,
        config_path=config,
        verbose=verbose,
    )

    # Parse date
    if date is None:
        target_date = datetime.now().date()
        logger.debug("using_today_as_target_date", date=str(target_date))
    else:
        try:
            parsed_date = date_parser.parse(date)
            target_date = parsed_date.date()
            logger.debug("parsed_date", input=date, parsed=str(target_date))
        except (ValueError, TypeError) as e:
            logger.error("date_parsing_failed", error=str(e), input=date)
            click.echo(f"Error parsing date: {e}", err=True)
            raise click.Abort()

    # Aggregate data from all sources
    try:
        logger.info("starting_data_aggregation", target_date=str(target_date))
        data = aggregate_data(target_date, config)
        logger.info("data_aggregation_completed", target_date=str(target_date))
    except Exception as e:
        logger.error("data_aggregation_failed", error=str(e), exc_info=True)
        click.echo(f"Error aggregating data: {e}", err=True)
        raise click.Abort()

    # Format and output
    logger.debug("formatting_output", format=format)
    if format.lower() == "json":
        output = format_as_json(data)
        click.echo(output)
    else:
        output = format_as_markdown(data)
        click.echo(output)

    logger.info("pkm_tool_completed", output_format=format)


if __name__ == "__main__":
    main()
