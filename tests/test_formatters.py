"""Tests for formatters."""

from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from pkm_tool.formatters import (
    format_as_json,
    format_as_markdown,
    format_filename,
    identify_section,
    merge_sections,
    parse_existing_file,
    write_report_to_file,
)
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


def test_format_filename_basic() -> None:
    """Test basic filename formatting."""
    template = "{date} ({day_abbr}).{format}"
    target_date = date(2025, 11, 21)  # Friday

    filename = format_filename(template, target_date, "markdown")
    assert filename == "2025-11-21 (Fri).md"


def test_format_filename_json() -> None:
    """Test filename formatting with JSON format."""
    template = "{date} ({day_abbr}).{format}"
    target_date = date(2025, 11, 22)  # Saturday

    filename = format_filename(template, target_date, "json")
    assert filename == "2025-11-22 (Sat).json"


def test_format_filename_components() -> None:
    """Test filename with individual date components."""
    template = "{year}/{month}/{day}-{day_abbr}.{format}"
    target_date = date(2025, 11, 21)  # Friday

    filename = format_filename(template, target_date, "markdown")
    assert filename == "2025/11/21-Fri.md"


def test_identify_section_calendar() -> None:
    """Test section identification for calendar events."""
    assert identify_section("## 📅 Calendar Events") == "calendar_events"
    assert identify_section("## Calendar Events") == "calendar_events"
    assert identify_section("## calendar events") == "calendar_events"


def test_identify_section_github() -> None:
    """Test section identification for GitHub activities."""
    assert identify_section("## 🐙 GitHub Activities") == "github_activities"
    assert identify_section("## GitHub Activities") == "github_activities"
    assert identify_section("## github") == "github_activities"


def test_identify_section_things() -> None:
    """Test section identification for Things tasks."""
    assert identify_section("## ✅ Things - Completed Tasks") == "things_tasks"
    assert identify_section("## Things") == "things_tasks"
    assert identify_section("## completed tasks") == "things_tasks"


def test_identify_section_unknown() -> None:
    """Test section identification returns None for unknown sections."""
    assert identify_section("## My Personal Notes") is None
    assert identify_section("## Random Section") is None


def test_parse_existing_file_empty() -> None:
    """Test parsing a nonexistent file."""
    sections = parse_existing_file(Path("nonexistent.md"))
    assert "_preamble" in sections
    assert "_postamble" in sections
    assert sections["_preamble"] == ""
    assert sections["_postamble"] == ""


def test_parse_existing_file_with_pkm_sections() -> None:
    """Test parsing file with PKM sections."""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        content = """# Daily Report - 2025-11-21

My personal notes here.

## 📅 Calendar Events

- **10:00 - 11:00** Team Meeting

## 🐙 GitHub Activities

- **14:30** Fixed bug

## My Personal Section

More personal notes.
"""
        test_file.write_text(content)

        sections = parse_existing_file(test_file)

        assert "My personal notes here" in sections["_preamble"]
        assert "calendar_events" in sections
        assert "Calendar Events" in sections["calendar_events"]
        assert "github_activities" in sections
        assert "GitHub Activities" in sections["github_activities"]
        assert "My Personal Section" in sections["_postamble"]


def test_merge_sections_preserve_preamble_postamble() -> None:
    """Test that merge preserves preamble and postamble."""
    existing = {
        "_preamble": "# My Daily Note\n\nPersonal thoughts.",
        "calendar_events": "## Old calendar stuff",
        "_postamble": "## My Evening Reflection\n\nThis was a good day.",
    }

    new_data = AggregatedData(
        date=date(2025, 11, 21),
        calendar_events=[
            Event(
                title="New Meeting",
                start=datetime(2025, 11, 21, 10, 0),
                end=datetime(2025, 11, 21, 11, 0),
            )
        ],
    )

    merged = merge_sections(existing, new_data, "markdown")

    assert "Personal thoughts" in merged
    assert "New Meeting" in merged
    assert "My Evening Reflection" in merged
    assert "Old calendar stuff" not in merged  # Old PKM data replaced


def test_merge_sections_append_new_sections() -> None:
    """Test that merge appends new PKM sections."""
    existing = {
        "_preamble": "# My Daily Note",
        "calendar_events": "## Calendar Events\n\n- Old event",
        "_postamble": "",
    }

    new_data = AggregatedData(
        date=date(2025, 11, 21),
        calendar_events=[
            Event(
                title="New Meeting",
                start=datetime(2025, 11, 21, 10, 0),
                end=datetime(2025, 11, 21, 11, 0),
            )
        ],
        github_activities=[
            GitHubActivity(
                type="commit",
                title="Fixed bug",
                url="https://github.com/test/repo",
                repository="test/repo",
                timestamp=datetime(2025, 11, 21, 14, 30),
            )
        ],
    )

    merged = merge_sections(existing, new_data, "markdown")

    assert "New Meeting" in merged
    assert "GitHub Activities" in merged  # New section appended
    assert "Fixed bug" in merged


def test_write_report_to_file_creates_directory() -> None:
    """Test that write_report_to_file creates output directory."""
    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "subdir" / "report.md"
        data = AggregatedData(date=date(2025, 11, 21))

        write_report_to_file(data, output_path, "markdown", merge_existing=False)

        assert output_path.exists()
        assert output_path.parent.exists()


def test_write_report_to_file_json_overwrites() -> None:
    """Test that JSON mode always overwrites."""
    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "report.json"

        # Write initial file
        data1 = AggregatedData(date=date(2025, 11, 21))
        write_report_to_file(data1, output_path, "json", merge_existing=True)

        content1 = output_path.read_text()

        # Write again with different data
        data2 = AggregatedData(
            date=date(2025, 11, 22),
            metadata={"test": "value"},
        )
        write_report_to_file(data2, output_path, "json", merge_existing=True)

        content2 = output_path.read_text()

        assert content1 != content2
        assert "2025-11-22" in content2


def test_write_report_to_file_markdown_merges() -> None:
    """Test that Markdown mode merges with existing content."""
    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "report.md"

        # Write initial file with manual content
        initial_content = """# My Daily Note

Personal thoughts here.

## My Section

Manual notes.
"""
        output_path.write_text(initial_content)

        # Write PKM data
        data = AggregatedData(
            date=date(2025, 11, 21),
            calendar_events=[
                Event(
                    title="Meeting",
                    start=datetime(2025, 11, 21, 10, 0),
                    end=datetime(2025, 11, 21, 11, 0),
                )
            ],
        )
        write_report_to_file(data, output_path, "markdown", merge_existing=True)

        final_content = output_path.read_text()

        assert "Personal thoughts here" in final_content  # Preamble preserved
        assert "Calendar Events" in final_content  # PKM section added
        assert "Meeting" in final_content
        assert "My Section" in final_content  # Postamble preserved
