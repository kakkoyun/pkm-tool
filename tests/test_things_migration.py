"""Tests for Things migration to things-py library."""

from datetime import date, datetime
from unittest.mock import patch

import pytest

from pkm_tool.models import ThingsTask
from pkm_tool.sources.things import fetch_things_tasks


@pytest.fixture
def mock_things_data():
    """Mock data from things-py library."""
    return [
        {
            "uuid": "task1",
            "type": "to-do",
            "title": "Complete project documentation",
            "status": "completed",
            "project": "proj1",
            "project_title": "Documentation Sprint",
            "tags": ["docs", "high-priority"],
            "stop_date": "2025-11-21 14:30:00",
            "created": "2025-11-20 10:00:00",
            "modified": "2025-11-21 14:30:00",
        },
        {
            "uuid": "task2",
            "type": "to-do",
            "title": "Review pull request",
            "status": "completed",
            "project": None,
            "project_title": None,
            "tags": [],
            "stop_date": "2025-11-21 16:45:30",
            "created": "2025-11-21 12:00:00",
            "modified": "2025-11-21 16:45:30",
        },
        {
            "uuid": "task3",
            "type": "to-do",
            "title": "Task from different date",
            "status": "completed",
            "project": None,
            "project_title": None,
            "tags": ["testing"],
            "stop_date": "2025-11-20 10:00:00",
            "created": "2025-11-19 10:00:00",
            "modified": "2025-11-20 10:00:00",
        },
        {
            "uuid": "task4",
            "type": "to-do",
            "title": "Another task from target date",
            "status": "completed",
            "project": "proj2",
            "project_title": "Code Review",
            "tags": ["review"],
            "stop_date": "2025-11-21 09:15:20",
            "created": "2025-11-21 08:00:00",
            "modified": "2025-11-21 09:15:20",
        },
    ]


def test_fetch_things_tasks_on_macos(mock_things_data):
    """Test fetching tasks on macOS with valid data."""
    target_date = date(2025, 11, 21)

    with (
        patch("platform.system", return_value="Darwin"),
        patch("things.todos", return_value=mock_things_data),
    ):
        result = fetch_things_tasks(target_date, {})

    # Should return 3 tasks (task1, task2, task4 completed on 2025-11-21)
    assert len(result) == 3
    assert all(isinstance(task, ThingsTask) for task in result)

    # Verify first task (sorted by completion time)
    assert result[0].title == "Another task from target date"
    assert result[0].completed_date == datetime(2025, 11, 21, 9, 15, 20)
    assert result[0].project == "Code Review"
    assert result[0].tags == ["review"]

    # Verify second task
    assert result[1].title == "Complete project documentation"
    assert result[1].completed_date == datetime(2025, 11, 21, 14, 30, 0)
    assert result[1].project == "Documentation Sprint"
    assert result[1].tags == ["docs", "high-priority"]

    # Verify third task
    assert result[2].title == "Review pull request"
    assert result[2].completed_date == datetime(2025, 11, 21, 16, 45, 30)
    assert result[2].project is None
    assert result[2].tags == []


def test_fetch_things_tasks_on_non_macos():
    """Test that function returns empty list on non-macOS platforms."""
    target_date = date(2025, 11, 21)

    with patch("platform.system", return_value="Linux"):
        result = fetch_things_tasks(target_date, {})

    assert result == []


def test_fetch_things_tasks_empty_results():
    """Test handling of empty results from things-py."""
    target_date = date(2025, 11, 21)

    with (
        patch("platform.system", return_value="Darwin"),
        patch("things.todos", return_value=[]),
    ):
        result = fetch_things_tasks(target_date, {})

    assert result == []


def test_fetch_things_tasks_no_matching_date(mock_things_data):
    """Test filtering when no tasks match target date."""
    target_date = date(2025, 11, 22)  # Different date

    with (
        patch("platform.system", return_value="Darwin"),
        patch("things.todos", return_value=mock_things_data),
    ):
        result = fetch_things_tasks(target_date, {})

    assert result == []


def test_fetch_things_tasks_library_error():
    """Test graceful error handling when things-py raises exception."""
    target_date = date(2025, 11, 21)

    with (
        patch("platform.system", return_value="Darwin"),
        patch(
            "things.todos",
            side_effect=Exception("Database not found"),
        ),
    ):
        result = fetch_things_tasks(target_date, {})

    assert result == []


def test_fetch_things_tasks_with_null_fields():
    """Test handling of tasks with null/missing fields."""
    target_date = date(2025, 11, 21)
    tasks_with_nulls = [
        {
            "uuid": "task1",
            "type": "to-do",
            "title": "Task with minimal data",
            "status": "completed",
            "project": None,
            "project_title": None,
            "tags": None,  # None instead of empty list
            "stop_date": "2025-11-21 10:00:00",
            "created": "2025-11-21 09:00:00",
            "modified": "2025-11-21 10:00:00",
        }
    ]

    with (
        patch("platform.system", return_value="Darwin"),
        patch("things.todos", return_value=tasks_with_nulls),
    ):
        result = fetch_things_tasks(target_date, {})

    assert len(result) == 1
    assert result[0].title == "Task with minimal data"
    assert result[0].project is None
    assert result[0].tags == []  # Should convert None to empty list


def test_fetch_things_tasks_date_filtering_precision():
    """Test that date filtering is precise (doesn't include nearby dates)."""
    target_date = date(2025, 11, 21)
    tasks = [
        {
            "uuid": "task1",
            "type": "to-do",
            "title": "Late on previous day",
            "status": "completed",
            "stop_date": "2025-11-20 23:59:59",  # Just before target date
            "project": None,
            "project_title": None,
            "tags": [],
            "created": "2025-11-20 10:00:00",
            "modified": "2025-11-20 23:59:59",
        },
        {
            "uuid": "task2",
            "type": "to-do",
            "title": "Start of target day",
            "status": "completed",
            "stop_date": "2025-11-21 00:00:00",  # Exactly at start
            "project": None,
            "project_title": None,
            "tags": [],
            "created": "2025-11-21 00:00:00",
            "modified": "2025-11-21 00:00:00",
        },
        {
            "uuid": "task3",
            "type": "to-do",
            "title": "End of target day",
            "status": "completed",
            "stop_date": "2025-11-21 23:59:59",  # Just before next day
            "project": None,
            "project_title": None,
            "tags": [],
            "created": "2025-11-21 10:00:00",
            "modified": "2025-11-21 23:59:59",
        },
        {
            "uuid": "task4",
            "type": "to-do",
            "title": "Start of next day",
            "status": "completed",
            "stop_date": "2025-11-22 00:00:00",  # Just after target date
            "project": None,
            "project_title": None,
            "tags": [],
            "created": "2025-11-21 10:00:00",
            "modified": "2025-11-22 00:00:00",
        },
    ]

    with (
        patch("platform.system", return_value="Darwin"),
        patch("things.todos", return_value=tasks),
    ):
        result = fetch_things_tasks(target_date, {})

    assert len(result) == 2  # Only task2 and task3
    assert result[0].title == "Start of target day"
    assert result[1].title == "End of target day"


def test_fetch_things_tasks_model_validation():
    """Test that returned data matches ThingsTask model structure."""
    target_date = date(2025, 11, 21)
    mock_data = [
        {
            "uuid": "task1",
            "type": "to-do",
            "title": "Test task",
            "status": "completed",
            "project": None,
            "project_title": "My Project",
            "tags": ["tag1", "tag2"],
            "stop_date": "2025-11-21 12:00:00",
            "created": "2025-11-21 10:00:00",
            "modified": "2025-11-21 12:00:00",
        }
    ]

    with (
        patch("platform.system", return_value="Darwin"),
        patch("things.todos", return_value=mock_data),
    ):
        result = fetch_things_tasks(target_date, {})

    assert len(result) == 1
    task = result[0]

    # Verify model structure
    assert hasattr(task, "title")
    assert hasattr(task, "completed_date")
    assert hasattr(task, "project")
    assert hasattr(task, "tags")

    # Verify types
    assert isinstance(task.title, str)
    assert isinstance(task.completed_date, datetime)
    assert task.project is None or isinstance(task.project, str)
    assert isinstance(task.tags, list)
