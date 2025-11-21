"""Tests for formatters."""

import json
from datetime import date, datetime

from pkm_tool.formatters import (
    format_as_json,
    format_as_markdown,
    format_reports_as_json,
    format_reports_as_markdown,
)
from pkm_tool.models import (
    AggregatedData,
    Event,
    GitHubActivity,
    WhoopRecovery,
    WhoopSleep,
    WhoopWorkout,
)


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


def test_format_as_markdown_with_skipped_sources() -> None:
    """Skipped sources should be presented in Markdown output."""
    data = AggregatedData(
        date=date(2025, 11, 22),
        metadata={"github_skipped": "weekend (source_config)"},
    )

    output = format_as_markdown(data)
    assert "Skipped Sources" in output
    assert "GitHub" in output


def test_format_reports_as_markdown_summary() -> None:
    """Multi-day markdown output should include summary and separators."""
    day_one = AggregatedData(date=date(2025, 11, 20))
    day_two = AggregatedData(date=date(2025, 11, 21))

    output = format_reports_as_markdown([day_one, day_two], (day_one.date, day_two.date))

    assert "# Daily Reports Summary" in output
    assert output.count("# Daily Report -") == 2
    assert "---" in output


def test_format_reports_as_json_summary() -> None:
    """Multi-day JSON output should include leading summary entry."""
    day_one = AggregatedData(date=date(2025, 11, 20))
    day_two = AggregatedData(date=date(2025, 11, 21))

    output = format_reports_as_json([day_one, day_two], (day_one.date, day_two.date))
    payload = json.loads(output)

    assert isinstance(payload, list)
    assert payload[0]["summary"]["days"] == 2
    assert payload[1]["date"] == "2025-11-20"


def test_format_as_markdown_with_whoop_data() -> None:
    """Whoop sections should appear when data is present."""
    recovery = WhoopRecovery(
        recovery_score=82.0,
        hrv=74.5,
        resting_heart_rate=48,
        spo2=97.0,
        skin_temp=33.2,
    )
    sleep = WhoopSleep(
        start=datetime(2025, 11, 21, 0, 30),
        end=datetime(2025, 11, 21, 8, 5),
        duration_minutes=455,
        sleep_efficiency=92.0,
        deep_sleep_minutes=120,
        light_sleep_minutes=200,
        rem_sleep_minutes=90,
    )
    workout = WhoopWorkout(
        start=datetime(2025, 11, 21, 18, 0),
        end=datetime(2025, 11, 21, 19, 0),
        sport_name="Running",
        strain=14.3,
        duration_minutes=60,
        average_heart_rate=150,
        max_heart_rate=170,
    )
    data = AggregatedData(
        date=date(2025, 11, 21),
        whoop_recovery=recovery,
        whoop_sleep=[sleep],
        whoop_workouts=[workout],
    )

    output = format_as_markdown(data)
    assert "Whoop Health Data" in output
    assert "Recovery" in output
    assert "Sleep" in output
    assert "Workouts" in output
