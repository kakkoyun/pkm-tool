"""Apple Calendar integration."""

import subprocess
from datetime import date, datetime
from typing import Any

import structlog

from pkm_tool.models import Event

logger = structlog.get_logger(__name__)


def fetch_calendar_events(target_date: date, config: dict[str, Any]) -> list[Event]:
    """
    Fetch calendar events from Apple Calendar.

    Uses AppleScript to query Calendar.app on macOS.

    Args:
        target_date: Date to fetch events for
        config: Configuration dictionary

    Returns:
        List of Event objects (empty list on error or non-macOS)
    """
    logger.debug("apple_calendar_fetch_started", date=str(target_date))

    # Check if running on macOS
    try:
        result = subprocess.run(["uname"], capture_output=True, text=True, check=True, timeout=5)
        if result.stdout.strip() != "Darwin":
            # Not on macOS, return empty list
            logger.debug(
                "apple_calendar_not_macos",
                message="Apple Calendar only available on macOS",
            )
            return []
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.error("apple_calendar_platform_check_failed", error=str(e), exc_info=True)
        return []

    # Build AppleScript to fetch events
    start_date = datetime.combine(target_date, datetime.min.time())
    end_date = datetime.combine(target_date, datetime.max.time())

    # AppleScript to fetch events
    apple_script = f"""
    tell application "Calendar"
        set theEvents to {{}}
        repeat with c in calendars
            set dayEvents to (every event of c whose (start date ≤ date "{end_date}") ¬
                and (end date ≥ date "{start_date}"))
            set theEvents to theEvents & dayEvents
        end repeat

        set eventList to {{}}
        repeat with e in theEvents
            set eventInfo to {{}}
            set eventInfo to eventInfo & (summary of e as string)
            set eventInfo to eventInfo & "|"
            set eventInfo to eventInfo & (start date of e as string)
            set eventInfo to eventInfo & "|"
            set eventInfo to eventInfo & (end date of e as string)
            set eventInfo to eventInfo & "|"
            try
                set eventInfo to eventInfo & (description of e as string)
            on error
                set eventInfo to eventInfo & ""
            end try
            set eventInfo to eventInfo & "|"
            try
                set eventInfo to eventInfo & (location of e as string)
            on error
                set eventInfo to eventInfo & ""
            end try
            set eventList to eventList & {{eventInfo as string}}
        end repeat

        return eventList
    end tell
    """

    try:
        logger.debug("apple_calendar_executing_applescript")
        result = subprocess.run(
            ["osascript", "-e", apple_script],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        events = []
        # Parse the output (would need proper parsing based on AppleScript output format)
        # This is a placeholder implementation
        # In a real implementation, you'd parse the AppleScript output

        logger.info("apple_calendar_events_fetched", event_count=len(events))
        return events
    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        # Handle all errors at top level for consistent error reporting
        logger.error("apple_calendar_fetch_failed", error=str(e), exc_info=True)
        return []
