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
    WhoopRecovery,
    WhoopSleep,
    WhoopWorkout,
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


def test_whoop_recovery_creation() -> None:
    """Test WhoopRecovery model creation."""
    recovery = WhoopRecovery(
        recovery_score=85.0,
        hrv=65.0,
        resting_heart_rate=48,
        spo2=97.5,
        skin_temp=36.2,
    )
    assert recovery.recovery_score == 85.0
    assert recovery.hrv == 65.0
    assert recovery.resting_heart_rate == 48
    assert recovery.spo2 == 97.5


def test_whoop_recovery_minimal() -> None:
    """Test WhoopRecovery with minimal required fields."""
    recovery = WhoopRecovery(
        recovery_score=75.0,
        hrv=55.0,
        resting_heart_rate=52,
    )
    assert recovery.recovery_score == 75.0
    assert recovery.spo2 is None
    assert recovery.skin_temp is None


def test_whoop_sleep_creation() -> None:
    """Test WhoopSleep model creation."""
    sleep = WhoopSleep(
        start=datetime(2025, 11, 20, 23, 0, 0),
        end=datetime(2025, 11, 21, 7, 0, 0),
        duration_minutes=480,
        sleep_efficiency=95.0,
        light_sleep_minutes=270,
        deep_sleep_minutes=135,
        rem_sleep_minutes=75,
        awake_minutes=15,
    )
    assert sleep.duration_minutes == 480
    assert sleep.sleep_efficiency == 95.0
    assert sleep.deep_sleep_minutes == 135


def test_whoop_sleep_minimal() -> None:
    """Test WhoopSleep with minimal required fields."""
    sleep = WhoopSleep(
        start=datetime(2025, 11, 20, 22, 30, 0),
        end=datetime(2025, 11, 21, 6, 30, 0),
        duration_minutes=480,
    )
    assert sleep.duration_minutes == 480
    assert sleep.sleep_efficiency is None
    assert sleep.light_sleep_minutes is None


def test_whoop_workout_creation() -> None:
    """Test WhoopWorkout model creation."""
    workout = WhoopWorkout(
        start=datetime(2025, 11, 21, 6, 0, 0),
        end=datetime(2025, 11, 21, 6, 45, 0),
        sport_name="Running",
        strain=15.2,
        duration_minutes=45,
        average_heart_rate=145,
        max_heart_rate=165,
        calories=450,
    )
    assert workout.sport_name == "Running"
    assert workout.strain == 15.2
    assert workout.average_heart_rate == 145


def test_whoop_workout_minimal() -> None:
    """Test WhoopWorkout with minimal required fields."""
    workout = WhoopWorkout(
        start=datetime(2025, 11, 21, 7, 0, 0),
        end=datetime(2025, 11, 21, 7, 30, 0),
        sport_name="Cycling",
        strain=12.5,
        duration_minutes=30,
    )
    assert workout.sport_name == "Cycling"
    assert workout.average_heart_rate is None
    assert workout.calories is None


def test_aggregated_data_with_whoop() -> None:
    """Test AggregatedData with Whoop data."""
    recovery = WhoopRecovery(
        recovery_score=85.0,
        hrv=65.0,
        resting_heart_rate=48,
    )
    sleep = WhoopSleep(
        start=datetime(2025, 11, 20, 23, 0, 0),
        end=datetime(2025, 11, 21, 7, 0, 0),
        duration_minutes=480,
    )
    workout = WhoopWorkout(
        start=datetime(2025, 11, 21, 6, 0, 0),
        end=datetime(2025, 11, 21, 6, 45, 0),
        sport_name="Running",
        strain=15.2,
        duration_minutes=45,
    )

    data = AggregatedData(
        date=date(2025, 11, 21),
        whoop_recovery=recovery,
        whoop_sleep=[sleep],
        whoop_workouts=[workout],
    )

    assert data.whoop_recovery is not None
    assert data.whoop_recovery.recovery_score == 85.0
    assert len(data.whoop_sleep) == 1
    assert len(data.whoop_workouts) == 1
    assert data.whoop_workouts[0].sport_name == "Running"
