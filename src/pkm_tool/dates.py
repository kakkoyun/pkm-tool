"""Shared date parsing utilities.

Provides a single source of truth for parsing date strings across the CLI,
MCP server, and REST API. Supports relative dates (yesterday, today, tomorrow),
ISO format, and natural language via python-dateutil.
"""

from datetime import date, datetime, timedelta

from dateutil import parser as date_parser


def parse_relative_date(date_input: str) -> date | None:
    """Parse relative date strings like 'yesterday', 'today', 'tomorrow'.

    Args:
        date_input: Relative date string (case-insensitive)

    Returns:
        Parsed date object or None if not a recognized relative date
    """
    today = datetime.now().date()
    normalized = date_input.lower().strip()

    relative_dates = {
        "today": timedelta(days=0),
        "yesterday": timedelta(days=-1),
        "tomorrow": timedelta(days=1),
    }

    if normalized in relative_dates:
        return today + relative_dates[normalized]

    return None


def parse_date(date_input: str | None) -> date:
    """Parse date string into date object.

    Supports:
    - None: returns today's date
    - Relative dates: 'yesterday', 'today', 'tomorrow' (case-insensitive)
    - Absolute dates: YYYY-MM-DD, natural language via dateutil

    Args:
        date_input: Date string or None for today

    Returns:
        Parsed date object

    Raises:
        ValueError: If date string cannot be parsed
    """
    if date_input is None:
        return datetime.now().date()

    # Try relative date parsing first
    relative_result = parse_relative_date(date_input)
    if relative_result is not None:
        return relative_result

    # Fall back to dateutil for absolute dates
    try:
        parsed = date_parser.parse(date_input)
        return parsed.date()
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid date format: {date_input}") from e
