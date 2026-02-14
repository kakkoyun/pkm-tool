"""Tests for shared date parsing utilities."""

from datetime import date, datetime, timedelta

import pytest

from pkm_tool.dates import parse_date, parse_relative_date


class TestParseRelativeDate:
    """Test relative date parsing."""

    def test_today(self):
        result = parse_relative_date("today")
        assert result == datetime.now().date()

    def test_yesterday(self):
        result = parse_relative_date("yesterday")
        assert result == datetime.now().date() - timedelta(days=1)

    def test_tomorrow(self):
        result = parse_relative_date("tomorrow")
        assert result == datetime.now().date() + timedelta(days=1)

    def test_case_insensitive(self):
        result = parse_relative_date("YESTERDAY")
        assert result == datetime.now().date() - timedelta(days=1)

    def test_with_whitespace(self):
        result = parse_relative_date("  today  ")
        assert result == datetime.now().date()

    def test_unknown_returns_none(self):
        assert parse_relative_date("last week") is None

    def test_empty_string_returns_none(self):
        assert parse_relative_date("") is None

    def test_nonsense_returns_none(self):
        assert parse_relative_date("asdf") is None


class TestParseDate:
    """Test full date parsing."""

    def test_none_returns_today(self):
        result = parse_date(None)
        assert result == datetime.now().date()

    def test_relative_yesterday(self):
        result = parse_date("yesterday")
        assert result == datetime.now().date() - timedelta(days=1)

    def test_iso_format(self):
        result = parse_date("2025-11-21")
        assert result == date(2025, 11, 21)

    def test_iso_with_time(self):
        result = parse_date("2025-11-21T14:30:00")
        assert result == date(2025, 11, 21)

    def test_natural_language(self):
        result = parse_date("Nov 21, 2025")
        assert result == date(2025, 11, 21)

    def test_invalid_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_date("not-a-date")

    def test_empty_string_raises_value_error(self):
        # Empty string is not None, so it goes through parsing
        # dateutil may or may not handle it — if it fails, ValueError is expected
        # This tests the contract, not dateutil internals
        with pytest.raises(ValueError):
            parse_date("")
