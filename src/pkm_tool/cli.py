"""CLI entry point for PKM tool."""

from datetime import datetime

import click
from dateutil import parser as date_parser

from pkm_tool.aggregator import aggregate_data
from pkm_tool.formatters import format_as_json, format_as_markdown


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
def main(date: str | None, format: str, config: str | None) -> None:
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
    # Parse date
    if date is None:
        target_date = datetime.now().date()
    else:
        try:
            parsed_date = date_parser.parse(date)
            target_date = parsed_date.date()
        except (ValueError, TypeError) as e:
            click.echo(f"Error parsing date: {e}", err=True)
            raise click.Abort()

    # Aggregate data from all sources
    try:
        data = aggregate_data(target_date, config)
    except Exception as e:
        click.echo(f"Error aggregating data: {e}", err=True)
        raise click.Abort()

    # Format and output
    if format.lower() == "json":
        output = format_as_json(data)
        click.echo(output)
    else:
        output = format_as_markdown(data)
        click.echo(output)


if __name__ == "__main__":
    main()
