"""Apple Calendar integration for macOS.

Fetches calendar events from Calendar.app using AppleScript.
Only works on macOS (Darwin) systems.
"""

import platform
import subprocess
from datetime import date, datetime
from typing import Any

import structlog

from pkm_tool.models import Event

logger = structlog.get_logger(__name__)

# Module-level cache to avoid re-running AppleScript for same date
_events_cache: dict[date, list[Event]] = {}

# Delimiters for structured AppleScript output
# Using triple angle brackets to avoid conflicts with event data
RECORD_SEPARATOR = "<<<RECORD>>>"
FIELD_SEPARATOR = "<<<FIELD>>>"

# Supported datetime formats for parsing AppleScript output
# AppleScript outputs dates in locale-dependent formats
DATETIME_FORMATS = [
    "%A, %B %d, %Y at %I:%M:%S %p",  # "Saturday, January 15, 2025 at 2:00:00 PM"
    "%A, %B %d, %Y at %H:%M:%S",  # "Saturday, January 15, 2025 at 14:00:00" (24-hour)
    "%B %d, %Y at %I:%M:%S %p",  # "January 15, 2025 at 2:00:00 PM" (no day name)
    "%B %d, %Y at %H:%M:%S",  # "January 15, 2025 at 14:00:00" (no day name, 24-hour)
    "%Y-%m-%d %H:%M:%S",  # "2025-01-15 14:00:00" (ISO-ish)
    "%m/%d/%Y %I:%M:%S %p",  # "01/15/2025 2:00:00 PM" (US format)
    "%d/%m/%Y %H:%M:%S",  # "15/01/2025 14:00:00" (European format)
]


def _clear_cache() -> None:
    """Clear the events cache.

    Useful for testing or when calendar data may have changed.
    """
    global _events_cache
    _events_cache = {}


def _is_macos() -> bool:
    """Check if running on macOS.

    Returns:
        True if running on macOS (Darwin), False otherwise.
    """
    return platform.system() == "Darwin"


def _parse_applescript_datetime(dt_str: str) -> datetime | None:
    """Parse a datetime string from AppleScript output.

    AppleScript outputs dates in locale-dependent formats. This function
    attempts to parse using multiple known formats.

    Args:
        dt_str: Datetime string from AppleScript output.

    Returns:
        Parsed datetime object, or None if parsing fails.
    """
    if not dt_str or not dt_str.strip():
        return None

    dt_str = dt_str.strip()

    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue

    logger.warning(
        "apple_calendar_datetime_parse_failed",
        datetime_string=dt_str,
        attempted_formats=len(DATETIME_FORMATS),
    )
    return None


def _parse_event_record(record: str) -> Event | None:
    """Parse a single event record from AppleScript output.

    Expected format: title<<<FIELD>>>start<<<FIELD>>>end<<<FIELD>>>description<<<FIELD>>>location

    Args:
        record: Single event record string with field separators.

    Returns:
        Event object if parsing succeeds, None otherwise.
    """
    if not record or not record.strip():
        return None

    fields = record.split(FIELD_SEPARATOR)

    if len(fields) < 3:
        logger.warning(
            "apple_calendar_record_insufficient_fields",
            field_count=len(fields),
            expected=5,
        )
        return None

    # Extract fields with safe indexing
    title = fields[0].strip() if len(fields) > 0 else ""
    start_str = fields[1].strip() if len(fields) > 1 else ""
    end_str = fields[2].strip() if len(fields) > 2 else ""
    description = fields[3].strip() if len(fields) > 3 else ""
    location = fields[4].strip() if len(fields) > 4 else ""

    # Title and dates are required
    if not title:
        logger.warning("apple_calendar_record_missing_title")
        return None

    start_dt = _parse_applescript_datetime(start_str)
    end_dt = _parse_applescript_datetime(end_str)

    if not start_dt or not end_dt:
        logger.warning(
            "apple_calendar_record_invalid_dates",
            title=title,
            start=start_str,
            end=end_str,
        )
        return None

    return Event(
        title=title,
        start=start_dt,
        end=end_dt,
        description=description if description else None,
        location=location if location else None,
    )


def _parse_applescript_output(output: str) -> list[Event]:
    """Parse the full AppleScript output into Event objects.

    Args:
        output: Raw AppleScript output with record and field separators.

    Returns:
        List of parsed Event objects. Invalid records are skipped.
    """
    if not output or not output.strip():
        return []

    events: list[Event] = []
    records = output.split(RECORD_SEPARATOR)

    for record in records:
        record = record.strip()
        if not record:
            continue

        event = _parse_event_record(record)
        if event:
            events.append(event)

    return events


def _build_applescript(target_date: date) -> str:
    """Build AppleScript to fetch calendar events for a specific date.

    The script queries all calendars for events starting on the target date.
    Uses structured delimiters for reliable parsing.

    Args:
        target_date: Date to fetch events for.

    Returns:
        AppleScript code as a string.
    """
    # AppleScript expects dates like "January 15, 2025"
    date_str = target_date.strftime("%B %d, %Y")

    # AppleScript with efficient string building using text item delimiters
    # and proper date comparison for events starting on target date
    # fmt: off

    return f'''
tell application "Calendar"
    set targetDateString to "{date_str}"
    set targetDate to date targetDateString
    set nextDay to targetDate + (1 * days)
    set fieldSep to "{FIELD_SEPARATOR}"

    set outputParts to {{}}

    repeat with cal in calendars
        try
            set dayEvents to (every event of cal whose ¬
                start date >= targetDate and start date < nextDay)
            repeat with evt in dayEvents
                set evtTitle to ""
                set evtStart to ""
                set evtEnd to ""
                set evtDesc to ""
                set evtLoc to ""

                try
                    set evtTitle to summary of evt as string
                end try

                try
                    set evtStart to start date of evt as string
                end try

                try
                    set evtEnd to end date of evt as string
                end try

                try
                    set evtDesc to description of evt as string
                on error
                    set evtDesc to ""
                end try

                try
                    set evtLoc to location of evt as string
                on error
                    set evtLoc to ""
                end try

                set eventRecord to evtTitle & fieldSep & evtStart & fieldSep ¬
                    & evtEnd & fieldSep & evtDesc & fieldSep & evtLoc
                set end of outputParts to eventRecord
            end repeat
        on error errMsg
            -- Skip calendars that cause errors (e.g., permission issues)
        end try
    end repeat

    -- Join all records with record separator
    set AppleScript's text item delimiters to "{RECORD_SEPARATOR}"
    set outputText to outputParts as string
    set AppleScript's text item delimiters to ""

    return outputText
end tell
'''
    # fmt: on


def fetch_calendar_events(target_date: date, config: dict[str, Any]) -> list[Event]:
    """Fetch calendar events from Apple Calendar for a specific date.

    Uses AppleScript to query Calendar.app on macOS. Returns cached results
    if available for the same date.

    Args:
        target_date: Date to fetch events for.
        config: Configuration dictionary (currently unused, reserved for future options).

    Returns:
        List of Event objects for the target date.
        Returns empty list on non-macOS systems, errors, or no events.
    """
    logger.debug("apple_calendar_fetch_started", date=str(target_date))

    # Check platform first
    if not _is_macos():
        logger.debug(
            "apple_calendar_not_macos",
            platform=platform.system(),
            message="Apple Calendar only available on macOS",
        )
        return []

    # Return cached results if available
    if target_date in _events_cache:
        cached_events = _events_cache[target_date]
        logger.debug(
            "apple_calendar_cache_hit",
            date=str(target_date),
            event_count=len(cached_events),
        )
        return cached_events

    # Build and execute AppleScript
    apple_script = _build_applescript(target_date)

    try:
        logger.debug("apple_calendar_executing_applescript", date=str(target_date))
        result = subprocess.run(
            ["osascript", "-e", apple_script],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check for AppleScript errors (non-zero exit or stderr output)
        if result.returncode != 0:
            logger.error(
                "apple_calendar_applescript_error",
                returncode=result.returncode,
                stderr=result.stderr.strip() if result.stderr else None,
            )
            return []

        # Parse the output
        output = result.stdout.strip()
        events = _parse_applescript_output(output)

        # Sort events by start time for consistent ordering
        events.sort(key=lambda e: e.start)

        # Cache the results
        _events_cache[target_date] = events

        logger.info(
            "apple_calendar_events_fetched",
            date=str(target_date),
            event_count=len(events),
        )
        return events

    except subprocess.TimeoutExpired:
        logger.error(
            "apple_calendar_timeout",
            date=str(target_date),
            timeout_seconds=30,
        )
        return []

    except FileNotFoundError:
        # osascript not found - should not happen on macOS
        logger.error(
            "apple_calendar_osascript_not_found",
            message="osascript command not found",
        )
        return []

    except subprocess.SubprocessError as e:
        logger.error(
            "apple_calendar_subprocess_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        return []

    except Exception as e:
        # Catch-all for unexpected errors - never crash the aggregator
        logger.error(
            "apple_calendar_unexpected_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return []
