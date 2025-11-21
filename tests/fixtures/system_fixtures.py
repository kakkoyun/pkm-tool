"""System-level mock fixtures (subprocess, SQLite, etc.)."""

import sqlite3
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_platform_macos(mocker: Mock) -> Mock:
    """Mock platform detection to return macOS."""
    mock_result = Mock()
    mock_result.stdout = "Darwin\n"
    mock_result.returncode = 0
    mock_subprocess = mocker.patch("pkm_tool.sources.apple_calendar.subprocess.run")
    mock_subprocess.return_value = mock_result
    return mock_subprocess


@pytest.fixture
def mock_platform_linux(mocker: Mock) -> Mock:
    """Mock platform detection to return Linux."""
    mock_result = Mock()
    mock_result.stdout = "Linux\n"
    mock_result.returncode = 0
    mock_subprocess = mocker.patch("pkm_tool.sources.apple_calendar.subprocess.run")
    mock_subprocess.return_value = mock_result
    return mock_subprocess


@pytest.fixture
def mock_osascript_success(mocker: Mock) -> Mock:
    """Mock successful osascript execution for Apple Calendar."""
    # First call for uname returns Darwin
    uname_result = Mock()
    uname_result.stdout = "Darwin\n"
    uname_result.returncode = 0

    # Second call for osascript returns event data
    osascript_result = Mock()
    # AppleScript returns data in a specific format
    osascript_result.stdout = (
        "Meeting with Team|Thursday, November 21, 2025 at 10:00:00 AM|"
        "Thursday, November 21, 2025 at 11:00:00 AM|Discuss project updates|Conference Room A\n"
    )
    osascript_result.returncode = 0

    mock_subprocess = mocker.patch("pkm_tool.sources.apple_calendar.subprocess.run")
    mock_subprocess.side_effect = [uname_result, osascript_result]
    return mock_subprocess


@pytest.fixture
def mock_osascript_error(mocker: Mock) -> Mock:
    """Mock failed osascript execution."""
    # First call for uname succeeds
    uname_result = Mock()
    uname_result.stdout = "Darwin\n"
    uname_result.returncode = 0

    mock_subprocess = mocker.patch("pkm_tool.sources.apple_calendar.subprocess.run")
    mock_subprocess.side_effect = [
        uname_result,
        subprocess.SubprocessError("osascript failed"),
    ]
    return mock_subprocess


@pytest.fixture
def mock_things_database(tmp_path: Path) -> Path:
    """Create a mock Things SQLite database with test data."""
    db_path = tmp_path / "test_things.sqlite"

    # Use context manager to ensure proper connection cleanup
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()

        # Create Things database schema (simplified)
        cursor.execute(
            """
            CREATE TABLE TMTask (
                uuid TEXT PRIMARY KEY,
                title TEXT,
                status INTEGER,
                stopDate REAL,
                project TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE TMTag (
                uuid TEXT PRIMARY KEY,
                title TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE TMTaskTag (
                tasks TEXT,
                tags TEXT
            )
        """
        )

        # Insert test data
        # Things uses seconds since 2001-01-01 as timestamp
        # For 2025-11-21 10:00:00: approximately 783777600 seconds from 2001-01-01
        # Let's use relative timestamps for the test date

        # Task 1: Complete project proposal (completed, with project and tags)
        task1_uuid = "task-uuid-1"
        project1_uuid = "project-uuid-1"
        tag1_uuid = "tag-uuid-1"
        tag2_uuid = "tag-uuid-2"

        cursor.execute(
            "INSERT INTO TMTask VALUES (?, ?, 3, 783777600.0, ?)",
            (task1_uuid, "Complete project proposal", project1_uuid),
        )
        cursor.execute("INSERT INTO TMTask VALUES (?, ?, 0, NULL, NULL)", (project1_uuid, "Work"))
        cursor.execute("INSERT INTO TMTag VALUES (?, ?)", (tag1_uuid, "urgent"))
        cursor.execute("INSERT INTO TMTag VALUES (?, ?)", (tag2_uuid, "writing"))
        cursor.execute("INSERT INTO TMTaskTag VALUES (?, ?)", (task1_uuid, tag1_uuid))
        cursor.execute("INSERT INTO TMTaskTag VALUES (?, ?)", (task1_uuid, tag2_uuid))

        # Task 2: Review pull request (completed, no project, one tag)
        task2_uuid = "task-uuid-2"
        tag3_uuid = "tag-uuid-3"

        cursor.execute(
            "INSERT INTO TMTask VALUES (?, ?, 3, 783788400.0, NULL)",
            (task2_uuid, "Review pull request"),
        )
        cursor.execute("INSERT INTO TMTag VALUES (?, ?)", (tag3_uuid, "code-review"))
        cursor.execute("INSERT INTO TMTaskTag VALUES (?, ?)", (task2_uuid, tag3_uuid))

        # Task 3: Buy groceries (completed, no project, no tags)
        task3_uuid = "task-uuid-3"
        cursor.execute(
            "INSERT INTO TMTask VALUES (?, ?, 3, 783795600.0, NULL)", (task3_uuid, "Buy groceries")
        )

        cursor.close()
        conn.commit()
        # Connection closed automatically by context manager

    return db_path


@pytest.fixture
def mock_things_database_path(mocker: Mock, mock_things_database: Path) -> Mock:
    """Mock Things database path to use test database."""
    mock_path = mocker.patch("pkm_tool.sources.things.Path")
    mock_path.home.return_value = mock_things_database.parent
    # Mock exists() to return True for the test database
    mock_instance = Mock()
    mock_instance.exists.return_value = True
    mock_path.return_value = mock_instance
    return mock_path


@pytest.fixture
def mock_things_database_missing(mocker: Mock) -> Mock:
    """Mock Things database as missing."""
    mock_path = mocker.patch("pkm_tool.sources.things.Path")
    mock_instance = Mock()
    mock_instance.exists.return_value = False
    mock_path.return_value = mock_instance
    return mock_path
