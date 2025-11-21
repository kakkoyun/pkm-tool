"""Tests for formatters."""

from datetime import date, datetime

from pkm_tool.formatters import format_as_json, format_as_markdown
from pkm_tool.models import AggregatedData, Event, GitHubActivity


def test_format_as_json() -> None:
    """Test JSON formatting."""
    data = AggregatedData(date=date(2025, 11, 21))
    output = format_as_json(data)

    assert '"date": "2025-11-21"' in output
    assert '"calendar_events": []' in output


def test_format_as_json_with_events() -> None:
    """Test JSON formatting with events."""
    event = Event(
        title="Test Meeting",
        start=datetime(2025, 11, 21, 10, 0),
        end=datetime(2025, 11, 21, 11, 0),
    )

    data = AggregatedData(
        date=date(2025, 11, 21),
        calendar_events=[event],
    )

    output = format_as_json(data)
    assert "Test Meeting" in output


def test_format_as_markdown() -> None:
    """Test Markdown formatting."""
    data = AggregatedData(date=date(2025, 11, 21))
    output = format_as_markdown(data)

    assert "# Daily Report - 2025-11-21" in output


def test_format_as_markdown_with_events() -> None:
    """Test Markdown formatting with events."""
    event = Event(
        title="Test Meeting",
        start=datetime(2025, 11, 21, 10, 0),
        end=datetime(2025, 11, 21, 11, 0),
        location="Office",
    )

    data = AggregatedData(
        date=date(2025, 11, 21),
        calendar_events=[event],
    )

    output = format_as_markdown(data)
    assert "Test Meeting" in output
    assert "10:00 - 11:00" in output
    assert "Office" in output


def test_format_as_markdown_with_github() -> None:
    """Test Markdown formatting with GitHub activities."""
    activity = GitHubActivity(
        type="commit",
        title="Fixed bug",
        url="https://github.com/test/repo",
        repository="test/repo",
        timestamp=datetime(2025, 11, 21, 10, 0),
    )

    data = AggregatedData(
        date=date(2025, 11, 21),
        github_activities=[activity],
    )

    output = format_as_markdown(data)
    assert "GitHub Activities" in output
    assert "Fixed bug" in output
    assert "test/repo" in output


def test_format_as_markdown_with_errors() -> None:
    """Test Markdown formatting with errors."""
    data = AggregatedData(
        date=date(2025, 11, 21),
        metadata={"github_error": "API rate limit exceeded"},
    )

    output = format_as_markdown(data)
    assert "Errors" in output
    assert "API rate limit exceeded" in output
