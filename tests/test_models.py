"""Tests for data models."""

from datetime import date, datetime

from pkm_tool.models import (
    AggregatedData,
    AtlassianItem,
    Event,
    GitHubActivity,
    GoogleDoc,
    ThingsTask,
    WakatimeActivity,
)


def test_event_creation() -> None:
    """Test Event model creation."""
    event = Event(
        title="Test Meeting",
        start=datetime(2025, 11, 21, 10, 0),
        end=datetime(2025, 11, 21, 11, 0),
        description="A test meeting",
        location="Conference Room",
    )
    assert event.title == "Test Meeting"
    assert event.location == "Conference Room"


def test_github_activity_creation() -> None:
    """Test GitHubActivity model creation."""
    activity = GitHubActivity(
        type="commit",
        title="Fixed bug",
        url="https://github.com/test/repo",
        repository="test/repo",
        timestamp=datetime(2025, 11, 21, 10, 0),
    )
    assert activity.type == "commit"
    assert activity.repository == "test/repo"


def test_atlassian_item_creation() -> None:
    """Test AtlassianItem model creation."""
    item = AtlassianItem(
        type="jira_issue",
        title="Test Issue",
        url="https://jira.example.com/browse/TEST-123",
        key="TEST-123",
        status="In Progress",
        updated=datetime(2025, 11, 21, 10, 0),
    )
    assert item.key == "TEST-123"
    assert item.status == "In Progress"


def test_things_task_creation() -> None:
    """Test ThingsTask model creation."""
    task = ThingsTask(
        title="Complete task",
        completed_date=datetime(2025, 11, 21, 10, 0),
        project="Project A",
        tags=["urgent", "work"],
    )
    assert task.title == "Complete task"
    assert len(task.tags) == 2


def test_wakatime_activity_creation() -> None:
    """Test WakatimeActivity model creation."""
    activity = WakatimeActivity(
        project="test-project",
        duration_seconds=3600,
        language="Python",
    )
    assert activity.project == "test-project"
    assert activity.duration_seconds == 3600


def test_google_doc_creation() -> None:
    """Test GoogleDoc model creation."""
    doc = GoogleDoc(
        title="Test Document",
        url="https://docs.google.com/document/d/123",
        opened_at=datetime(2025, 11, 21, 10, 0),
        doc_type="document",
    )
    assert doc.title == "Test Document"
    assert doc.doc_type == "document"


def test_aggregated_data_creation() -> None:
    """Test AggregatedData model creation."""
    data = AggregatedData(date=date(2025, 11, 21))
    assert data.date == date(2025, 11, 21)
    assert len(data.calendar_events) == 0
    assert len(data.github_activities) == 0


def test_aggregated_data_with_items() -> None:
    """Test AggregatedData with items."""
    event = Event(
        title="Meeting",
        start=datetime(2025, 11, 21, 10, 0),
        end=datetime(2025, 11, 21, 11, 0),
    )

    data = AggregatedData(
        date=date(2025, 11, 21),
        calendar_events=[event],
    )

    assert len(data.calendar_events) == 1
    assert data.calendar_events[0].title == "Meeting"
