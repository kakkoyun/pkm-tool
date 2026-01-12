"""Tests for Apple Calendar source module.

Tests the AppleScript-based calendar integration for macOS,
including datetime parsing, event record parsing, caching, and error handling.
"""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

from pkm_tool.sources.apple_calendar import (
    DATETIME_FORMATS,
    FIELD_SEPARATOR,
    RECORD_SEPARATOR,
    _build_applescript,
    _clear_cache,
    _is_macos,
    _parse_applescript_datetime,
    _parse_applescript_output,
    _parse_event_record,
    fetch_calendar_events,
)


class TestParseApplescriptDatetime:
    """Tests for datetime parsing from AppleScript output."""

    def test_parse_full_format_12_hour(self) -> None:
        """Test parsing full format with 12-hour time and AM/PM."""
        result = _parse_applescript_datetime("Saturday, January 15, 2025 at 2:00:00 PM")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 0
        assert result.second == 0

    def test_parse_full_format_24_hour(self) -> None:
        """Test parsing full format with 24-hour time."""
        result = _parse_applescript_datetime("Saturday, January 15, 2025 at 14:30:00")
        assert result is not None
        assert result.hour == 14
        assert result.minute == 30

    def test_parse_no_day_name_12_hour(self) -> None:
        """Test parsing without day name, 12-hour format."""
        result = _parse_applescript_datetime("January 15, 2025 at 9:15:00 AM")
        assert result is not None
        assert result.hour == 9
        assert result.minute == 15

    def test_parse_no_day_name_24_hour(self) -> None:
        """Test parsing without day name, 24-hour format."""
        result = _parse_applescript_datetime("January 15, 2025 at 09:15:00")
        assert result is not None
        assert result.hour == 9

    def test_parse_iso_format(self) -> None:
        """Test parsing ISO-ish format."""
        result = _parse_applescript_datetime("2025-01-15 14:00:00")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 14

    def test_parse_us_format(self) -> None:
        """Test parsing US format (MM/DD/YYYY)."""
        result = _parse_applescript_datetime("01/15/2025 2:00:00 PM")
        assert result is not None
        assert result.month == 1
        assert result.day == 15

    def test_parse_european_format(self) -> None:
        """Test parsing European format (DD/MM/YYYY)."""
        result = _parse_applescript_datetime("15/01/2025 14:00:00")
        assert result is not None
        assert result.day == 15
        assert result.month == 1

    def test_parse_empty_string_returns_none(self) -> None:
        """Test that empty string returns None."""
        assert _parse_applescript_datetime("") is None

    def test_parse_whitespace_only_returns_none(self) -> None:
        """Test that whitespace-only string returns None."""
        assert _parse_applescript_datetime("   ") is None

    def test_parse_none_input_returns_none(self) -> None:
        """Test that None input returns None."""
        assert _parse_applescript_datetime(None) is None  # type: ignore[arg-type]

    def test_parse_invalid_format_returns_none(self) -> None:
        """Test that invalid format returns None."""
        result = _parse_applescript_datetime("not a valid date")
        assert result is None

    def test_parse_strips_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        result = _parse_applescript_datetime("  2025-01-15 14:00:00  ")
        assert result is not None
        assert result.year == 2025

    def test_all_formats_in_constant(self) -> None:
        """Test that all formats in DATETIME_FORMATS are valid strptime formats."""
        test_dates = [
            "Saturday, January 15, 2025 at 2:00:00 PM",
            "Saturday, January 15, 2025 at 14:00:00",
            "January 15, 2025 at 2:00:00 PM",
            "January 15, 2025 at 14:00:00",
            "2025-01-15 14:00:00",
            "01/15/2025 2:00:00 PM",
            "15/01/2025 14:00:00",
        ]
        # Ensure we have same number of test cases as formats
        assert len(test_dates) == len(DATETIME_FORMATS)
        # Each test date should parse
        for dt_str in test_dates:
            result = _parse_applescript_datetime(dt_str)
            assert result is not None, f"Failed to parse: {dt_str}"


class TestParseEventRecord:
    """Tests for parsing single event records."""

    def test_parse_complete_record(self) -> None:
        """Test parsing a complete event record with all fields."""
        record = (
            f"Team Meeting{FIELD_SEPARATOR}"
            f"Saturday, January 15, 2025 at 2:00:00 PM{FIELD_SEPARATOR}"
            f"Saturday, January 15, 2025 at 3:00:00 PM{FIELD_SEPARATOR}"
            f"Weekly sync{FIELD_SEPARATOR}Conference Room A"
        )
        event = _parse_event_record(record)

        assert event is not None
        assert event.title == "Team Meeting"
        assert event.start.hour == 14
        assert event.end.hour == 15
        assert event.description == "Weekly sync"
        assert event.location == "Conference Room A"

    def test_parse_record_without_description(self) -> None:
        """Test parsing record with empty description."""
        record = (
            f"Quick Call{FIELD_SEPARATOR}2025-01-15 14:00:00{FIELD_SEPARATOR}"
            f"2025-01-15 14:30:00{FIELD_SEPARATOR}{FIELD_SEPARATOR}Office"
        )
        event = _parse_event_record(record)

        assert event is not None
        assert event.title == "Quick Call"
        assert event.description is None
        assert event.location == "Office"

    def test_parse_record_without_location(self) -> None:
        """Test parsing record with empty location."""
        record = (
            f"Phone Call{FIELD_SEPARATOR}2025-01-15 14:00:00{FIELD_SEPARATOR}"
            f"2025-01-15 14:30:00{FIELD_SEPARATOR}Call with client{FIELD_SEPARATOR}"
        )
        event = _parse_event_record(record)

        assert event is not None
        assert event.location is None
        assert event.description == "Call with client"

    def test_parse_minimal_record(self) -> None:
        """Test parsing record with only required fields (title, start, end)."""
        record = f"Lunch{FIELD_SEPARATOR}2025-01-15 12:00:00{FIELD_SEPARATOR}2025-01-15 13:00:00"
        event = _parse_event_record(record)

        assert event is not None
        assert event.title == "Lunch"
        assert event.description is None
        assert event.location is None

    def test_parse_empty_string_returns_none(self) -> None:
        """Test that empty string returns None."""
        assert _parse_event_record("") is None

    def test_parse_whitespace_only_returns_none(self) -> None:
        """Test that whitespace-only string returns None."""
        assert _parse_event_record("   ") is None

    def test_parse_insufficient_fields_returns_none(self) -> None:
        """Test that record with less than 3 fields returns None."""
        record = f"Title Only{FIELD_SEPARATOR}2025-01-15 14:00:00"
        assert _parse_event_record(record) is None

    def test_parse_missing_title_returns_none(self) -> None:
        """Test that record with empty title returns None."""
        record = f"{FIELD_SEPARATOR}2025-01-15 14:00:00{FIELD_SEPARATOR}2025-01-15 15:00:00"
        assert _parse_event_record(record) is None

    def test_parse_invalid_start_date_returns_none(self) -> None:
        """Test that record with invalid start date returns None."""
        record = f"Meeting{FIELD_SEPARATOR}invalid date{FIELD_SEPARATOR}2025-01-15 15:00:00"
        assert _parse_event_record(record) is None

    def test_parse_invalid_end_date_returns_none(self) -> None:
        """Test that record with invalid end date returns None."""
        record = f"Meeting{FIELD_SEPARATOR}2025-01-15 14:00:00{FIELD_SEPARATOR}invalid date"
        assert _parse_event_record(record) is None

    def test_parse_strips_whitespace_from_fields(self) -> None:
        """Test that whitespace is stripped from all fields."""
        record = (
            f"  Meeting  {FIELD_SEPARATOR}  2025-01-15 14:00:00  {FIELD_SEPARATOR}"
            f"  2025-01-15 15:00:00  {FIELD_SEPARATOR}  Notes  {FIELD_SEPARATOR}  Room 1  "
        )
        event = _parse_event_record(record)

        assert event is not None
        assert event.title == "Meeting"
        assert event.description == "Notes"
        assert event.location == "Room 1"


class TestParseApplescriptOutput:
    """Tests for parsing full AppleScript output."""

    def test_parse_single_event(self) -> None:
        """Test parsing output with single event."""
        output = (
            f"Meeting{FIELD_SEPARATOR}2025-01-15 14:00:00{FIELD_SEPARATOR}"
            f"2025-01-15 15:00:00{FIELD_SEPARATOR}Notes{FIELD_SEPARATOR}Office"
        )
        events = _parse_applescript_output(output)

        assert len(events) == 1
        assert events[0].title == "Meeting"

    def test_parse_multiple_events(self) -> None:
        """Test parsing output with multiple events."""
        sep = FIELD_SEPARATOR
        rec = RECORD_SEPARATOR
        output = (
            f"Event 1{sep}2025-01-15 09:00:00{sep}2025-01-15 10:00:00{sep}{sep}"
            f"{rec}"
            f"Event 2{sep}2025-01-15 14:00:00{sep}2025-01-15 15:00:00{sep}Description{sep}Location"
            f"{rec}"
            f"Event 3{sep}2025-01-15 16:00:00{sep}2025-01-15 17:00:00{sep}{sep}"
        )
        events = _parse_applescript_output(output)

        assert len(events) == 3
        assert events[0].title == "Event 1"
        assert events[1].title == "Event 2"
        assert events[2].title == "Event 3"

    def test_parse_empty_output(self) -> None:
        """Test parsing empty output."""
        assert _parse_applescript_output("") == []

    def test_parse_whitespace_only_output(self) -> None:
        """Test parsing whitespace-only output."""
        assert _parse_applescript_output("   \n\t  ") == []

    def test_parse_skips_invalid_records(self) -> None:
        """Test that invalid records are skipped without affecting valid ones."""
        sep = FIELD_SEPARATOR
        rec = RECORD_SEPARATOR
        output = (
            f"Valid Event{sep}2025-01-15 09:00:00{sep}2025-01-15 10:00:00{sep}{sep}"
            f"{rec}"
            f"Invalid{sep}bad data"  # Not enough fields
            f"{rec}"
            f"Another Valid{sep}2025-01-15 14:00:00{sep}2025-01-15 15:00:00{sep}{sep}"
        )
        events = _parse_applescript_output(output)

        assert len(events) == 2
        assert events[0].title == "Valid Event"
        assert events[1].title == "Another Valid"

    def test_parse_skips_empty_records(self) -> None:
        """Test that empty records between separators are skipped."""
        sep = FIELD_SEPARATOR
        rec = RECORD_SEPARATOR
        output = (
            f"Event 1{sep}2025-01-15 09:00:00{sep}2025-01-15 10:00:00{sep}{sep}"
            f"{rec}"
            f"   "  # Empty/whitespace record
            f"{rec}"
            f""  # Empty record
            f"{rec}"
            f"Event 2{sep}2025-01-15 14:00:00{sep}2025-01-15 15:00:00{sep}{sep}"
        )
        events = _parse_applescript_output(output)

        assert len(events) == 2


class TestClearCache:
    """Tests for cache clearing function."""

    def test_clear_cache_empties_cache(self) -> None:
        """Test that _clear_cache empties the module-level cache."""
        # Import the module to access the cache
        from pkm_tool.sources import apple_calendar

        # Manually add something to the cache
        test_date = date(2025, 1, 15)
        apple_calendar._events_cache[test_date] = []

        # Clear the cache
        _clear_cache()

        # Verify cache is empty
        assert len(apple_calendar._events_cache) == 0


class TestIsMacos:
    """Tests for macOS detection."""

    def test_is_macos_on_darwin(self) -> None:
        """Test that _is_macos returns True on Darwin."""
        with patch("platform.system", return_value="Darwin"):
            assert _is_macos() is True

    def test_is_macos_on_linux(self) -> None:
        """Test that _is_macos returns False on Linux."""
        with patch("platform.system", return_value="Linux"):
            assert _is_macos() is False

    def test_is_macos_on_windows(self) -> None:
        """Test that _is_macos returns False on Windows."""
        with patch("platform.system", return_value="Windows"):
            assert _is_macos() is False


class TestBuildApplescript:
    """Tests for AppleScript generation."""

    def test_build_applescript_contains_date(self) -> None:
        """Test that generated script contains the formatted date."""
        target_date = date(2025, 1, 15)
        script = _build_applescript(target_date)

        assert "January 15, 2025" in script

    def test_build_applescript_contains_separators(self) -> None:
        """Test that generated script contains the field and record separators."""
        target_date = date(2025, 1, 15)
        script = _build_applescript(target_date)

        assert FIELD_SEPARATOR in script
        assert RECORD_SEPARATOR in script

    def test_build_applescript_contains_calendar_tell(self) -> None:
        """Test that generated script tells Calendar application."""
        script = _build_applescript(date(2025, 1, 15))
        assert 'tell application "Calendar"' in script

    def test_build_applescript_different_dates(self) -> None:
        """Test that different dates produce different scripts."""
        script1 = _build_applescript(date(2025, 1, 15))
        script2 = _build_applescript(date(2025, 6, 20))

        assert "January 15, 2025" in script1
        assert "June 20, 2025" in script2


class TestFetchCalendarEvents:
    """Tests for the main fetch function."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        _clear_cache()

    def test_fetch_returns_empty_on_non_macos(self) -> None:
        """Test that fetch returns empty list on non-macOS systems."""
        with patch("pkm_tool.sources.apple_calendar._is_macos", return_value=False):
            events = fetch_calendar_events(date(2025, 1, 15), {})
        assert events == []

    def test_fetch_returns_cached_results(self) -> None:
        """Test that cached results are returned without running AppleScript."""
        from pkm_tool.models import Event
        from pkm_tool.sources import apple_calendar

        target_date = date(2025, 1, 15)
        cached_event = Event(
            title="Cached Event",
            start=datetime(2025, 1, 15, 10, 0),
            end=datetime(2025, 1, 15, 11, 0),
        )
        apple_calendar._events_cache[target_date] = [cached_event]

        with patch("pkm_tool.sources.apple_calendar._is_macos", return_value=True):
            with patch("subprocess.run") as mock_run:
                events = fetch_calendar_events(target_date, {})

                # subprocess.run should NOT be called due to cache hit
                mock_run.assert_not_called()
                assert len(events) == 1
                assert events[0].title == "Cached Event"

    def test_fetch_executes_applescript_on_macos(self) -> None:
        """Test that AppleScript is executed on macOS when cache is empty."""
        sep = FIELD_SEPARATOR
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = f"Meeting{sep}2025-01-15 14:00:00{sep}2025-01-15 15:00:00{sep}{sep}"

        with patch("pkm_tool.sources.apple_calendar._is_macos", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                events = fetch_calendar_events(date(2025, 1, 15), {})

                mock_run.assert_called_once()
                assert len(events) == 1
                assert events[0].title == "Meeting"

    def test_fetch_returns_empty_on_applescript_error(self) -> None:
        """Test that non-zero return code returns empty list."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "AppleScript error"

        with patch("pkm_tool.sources.apple_calendar._is_macos", return_value=True):
            with patch("subprocess.run", return_value=mock_result):
                events = fetch_calendar_events(date(2025, 1, 15), {})
                assert events == []

    def test_fetch_returns_empty_on_timeout(self) -> None:
        """Test that timeout returns empty list."""
        import subprocess

        with patch("pkm_tool.sources.apple_calendar._is_macos", return_value=True):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("osascript", 30)):
                events = fetch_calendar_events(date(2025, 1, 15), {})
                assert events == []

    def test_fetch_returns_empty_on_file_not_found(self) -> None:
        """Test that FileNotFoundError returns empty list."""
        with patch("pkm_tool.sources.apple_calendar._is_macos", return_value=True):
            with patch("subprocess.run", side_effect=FileNotFoundError("osascript")):
                events = fetch_calendar_events(date(2025, 1, 15), {})
                assert events == []

    def test_fetch_returns_empty_on_subprocess_error(self) -> None:
        """Test that SubprocessError returns empty list."""
        import subprocess

        with patch("pkm_tool.sources.apple_calendar._is_macos", return_value=True):
            with patch("subprocess.run", side_effect=subprocess.SubprocessError("error")):
                events = fetch_calendar_events(date(2025, 1, 15), {})
                assert events == []

    def test_fetch_returns_empty_on_unexpected_error(self) -> None:
        """Test that unexpected exceptions return empty list."""
        with patch("pkm_tool.sources.apple_calendar._is_macos", return_value=True):
            with patch("subprocess.run", side_effect=RuntimeError("unexpected")):
                events = fetch_calendar_events(date(2025, 1, 15), {})
                assert events == []

    def test_fetch_caches_results(self) -> None:
        """Test that successful fetch results are cached."""
        from pkm_tool.sources import apple_calendar

        sep = FIELD_SEPARATOR
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = f"Meeting{sep}2025-01-15 14:00:00{sep}2025-01-15 15:00:00{sep}{sep}"

        target_date = date(2025, 1, 15)

        with patch("pkm_tool.sources.apple_calendar._is_macos", return_value=True):
            with patch("subprocess.run", return_value=mock_result):
                fetch_calendar_events(target_date, {})

                # Verify results are cached
                assert target_date in apple_calendar._events_cache
                assert len(apple_calendar._events_cache[target_date]) == 1

    def test_fetch_sorts_events_by_start_time(self) -> None:
        """Test that fetched events are sorted by start time."""
        sep = FIELD_SEPARATOR
        rec = RECORD_SEPARATOR
        mock_result = MagicMock()
        mock_result.returncode = 0
        # Events in non-chronological order
        mock_result.stdout = (
            f"Evening{sep}2025-01-15 18:00:00{sep}2025-01-15 19:00:00{sep}{sep}"
            f"{rec}"
            f"Morning{sep}2025-01-15 09:00:00{sep}2025-01-15 10:00:00{sep}{sep}"
            f"{rec}"
            f"Afternoon{sep}2025-01-15 14:00:00{sep}2025-01-15 15:00:00{sep}{sep}"
        )

        with patch("pkm_tool.sources.apple_calendar._is_macos", return_value=True):
            with patch("subprocess.run", return_value=mock_result):
                events = fetch_calendar_events(date(2025, 1, 15), {})

                # Events should be sorted by start time
                assert len(events) == 3
                assert events[0].title == "Morning"
                assert events[1].title == "Afternoon"
                assert events[2].title == "Evening"

    def test_fetch_handles_empty_output(self) -> None:
        """Test handling of empty AppleScript output (no events)."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("pkm_tool.sources.apple_calendar._is_macos", return_value=True):
            with patch("subprocess.run", return_value=mock_result):
                events = fetch_calendar_events(date(2025, 1, 15), {})
                assert events == []
