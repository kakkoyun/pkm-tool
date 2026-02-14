"""Tests for Things source module."""

from datetime import date
from unittest.mock import patch

from pkm_tool.sources.things import fetch_things_tasks

TARGET_DATE = date(2025, 11, 21)


class TestFetchThingsTasks:
    """Test main fetch function."""

    def test_non_macos_returns_empty(self):
        """Returns empty on non-macOS platforms."""
        with patch("pkm_tool.sources.things.platform.system", return_value="Linux"):
            tasks = fetch_things_tasks(TARGET_DATE, {})
        assert tasks == []

    def test_fetch_completed_tasks(self):
        """Fetches and filters completed tasks by date."""
        mock_todos = [
            {
                "title": "Write docs",
                "stop_date": "2025-11-21 10:00:00",
                "project_title": "PKM Tool",
                "tags": ["writing", "urgent"],
            },
            {
                "title": "Review PR",
                "stop_date": "2025-11-21 14:30:00",
                "project_title": None,
                "tags": ["code-review"],
            },
        ]
        with (
            patch("pkm_tool.sources.things.platform.system", return_value="Darwin"),
            patch("things.todos", return_value=mock_todos),
        ):
            tasks = fetch_things_tasks(TARGET_DATE, {})
        assert len(tasks) == 2
        assert tasks[0].title == "Write docs"
        assert tasks[0].project == "PKM Tool"
        assert tasks[0].tags == ["writing", "urgent"]
        assert tasks[1].title == "Review PR"

    def test_filters_by_date(self):
        """Only returns tasks completed on target date."""
        mock_todos = [
            {
                "title": "Wrong date task",
                "stop_date": "2025-11-20 10:00:00",
                "project_title": None,
                "tags": [],
            },
            {
                "title": "Correct date task",
                "stop_date": "2025-11-21 10:00:00",
                "project_title": None,
                "tags": [],
            },
        ]
        with (
            patch("pkm_tool.sources.things.platform.system", return_value="Darwin"),
            patch("things.todos", return_value=mock_todos),
        ):
            tasks = fetch_things_tasks(TARGET_DATE, {})
        assert len(tasks) == 1
        assert tasks[0].title == "Correct date task"

    def test_missing_stop_date_skipped(self):
        """Tasks without stop_date are skipped."""
        mock_todos = [
            {"title": "No date", "stop_date": None, "project_title": None, "tags": []},
        ]
        with (
            patch("pkm_tool.sources.things.platform.system", return_value="Darwin"),
            patch("things.todos", return_value=mock_todos),
        ):
            tasks = fetch_things_tasks(TARGET_DATE, {})
        assert tasks == []

    def test_missing_title_skipped(self):
        """Tasks without title are skipped."""
        mock_todos = [
            {"title": None, "stop_date": "2025-11-21 10:00:00", "project_title": None, "tags": []},
        ]
        with (
            patch("pkm_tool.sources.things.platform.system", return_value="Darwin"),
            patch("things.todos", return_value=mock_todos),
        ):
            tasks = fetch_things_tasks(TARGET_DATE, {})
        assert tasks == []

    def test_empty_title_skipped(self):
        """Tasks with empty title are skipped."""
        mock_todos = [
            {"title": "", "stop_date": "2025-11-21 10:00:00", "project_title": None, "tags": []},
        ]
        with (
            patch("pkm_tool.sources.things.platform.system", return_value="Darwin"),
            patch("things.todos", return_value=mock_todos),
        ):
            tasks = fetch_things_tasks(TARGET_DATE, {})
        assert tasks == []

    def test_none_tags_handled(self):
        """None tags converted to empty list."""
        mock_todos = [
            {
                "title": "Task with none tags",
                "stop_date": "2025-11-21 10:00:00",
                "project_title": None,
                "tags": None,
            },
        ]
        with (
            patch("pkm_tool.sources.things.platform.system", return_value="Darwin"),
            patch("things.todos", return_value=mock_todos),
        ):
            tasks = fetch_things_tasks(TARGET_DATE, {})
        assert len(tasks) == 1
        assert tasks[0].tags == []

    def test_sorted_by_completion_time(self):
        """Tasks sorted by completion time."""
        mock_todos = [
            {
                "title": "Later task",
                "stop_date": "2025-11-21 16:00:00",
                "project_title": None,
                "tags": [],
            },
            {
                "title": "Earlier task",
                "stop_date": "2025-11-21 08:00:00",
                "project_title": None,
                "tags": [],
            },
        ]
        with (
            patch("pkm_tool.sources.things.platform.system", return_value="Darwin"),
            patch("things.todos", return_value=mock_todos),
        ):
            tasks = fetch_things_tasks(TARGET_DATE, {})
        assert tasks[0].title == "Earlier task"
        assert tasks[1].title == "Later task"

    def test_empty_logbook(self):
        """Empty completed todos list."""
        with (
            patch("pkm_tool.sources.things.platform.system", return_value="Darwin"),
            patch("things.todos", return_value=[]),
        ):
            tasks = fetch_things_tasks(TARGET_DATE, {})
        assert tasks == []

    def test_exception_returns_empty(self):
        """Returns empty on any exception."""
        with (
            patch("pkm_tool.sources.things.platform.system", return_value="Darwin"),
            patch("things.todos", side_effect=Exception("Database error")),
        ):
            tasks = fetch_things_tasks(TARGET_DATE, {})
        assert tasks == []

    def test_invalid_date_format_skipped(self):
        """Tasks with invalid date format are skipped."""
        mock_todos = [
            {
                "title": "Bad date format",
                "stop_date": "not-a-date",
                "project_title": None,
                "tags": [],
            },
        ]
        with (
            patch("pkm_tool.sources.things.platform.system", return_value="Darwin"),
            patch("things.todos", return_value=mock_todos),
        ):
            tasks = fetch_things_tasks(TARGET_DATE, {})
        assert tasks == []
