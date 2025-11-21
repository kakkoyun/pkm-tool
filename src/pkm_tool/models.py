"""Data models for PKM tool."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class Event(BaseModel):
    """Calendar event."""

    title: str
    start: datetime
    end: datetime
    description: str | None = None
    location: str | None = None


class GitHubActivity(BaseModel):
    """GitHub activity item."""

    type: str  # commit, pr, issue, review
    title: str
    url: str
    repository: str
    timestamp: datetime
    details: str | None = None


class AtlassianItem(BaseModel):
    """Jira/Confluence item."""

    type: str  # jira_issue, confluence_page
    title: str
    url: str
    key: str
    status: str | None = None
    updated: datetime


class ThingsTask(BaseModel):
    """Things task from logbook."""

    title: str
    completed_date: datetime
    project: str | None = None
    tags: list[str] = Field(default_factory=list)


class WakatimeActivity(BaseModel):
    """Wakatime coding activity."""

    project: str
    duration_seconds: int
    language: str | None = None


class GoogleDoc(BaseModel):
    """Google Docs document."""

    title: str
    url: str
    opened_at: datetime
    doc_type: str = "document"


class WhoopRecovery(BaseModel):
    """Whoop recovery data."""

    recovery_score: float  # 0-100%
    hrv: float  # Heart rate variability in milliseconds
    resting_heart_rate: int  # Beats per minute
    spo2: float | None = None  # Blood oxygen percentage
    skin_temp: float | None = None  # Skin temperature in Celsius


class WhoopSleep(BaseModel):
    """Whoop sleep cycle data."""

    start: datetime
    end: datetime
    duration_minutes: int
    sleep_efficiency: float | None = None  # Percentage
    light_sleep_minutes: int | None = None
    deep_sleep_minutes: int | None = None
    rem_sleep_minutes: int | None = None
    awake_minutes: int | None = None
    disturbances: int | None = None
    sleep_performance: float | None = None  # Percentage


class WhoopWorkout(BaseModel):
    """Whoop workout/activity data."""

    start: datetime
    end: datetime
    sport_name: str
    strain: float  # Whoop strain score
    duration_minutes: int
    average_heart_rate: int | None = None
    max_heart_rate: int | None = None
    calories: int | None = None


class AggregatedData(BaseModel):
    """Aggregated data from all sources."""

    date: date
    calendar_events: list[Event] = Field(default_factory=list)
    github_activities: list[GitHubActivity] = Field(default_factory=list)
    atlassian_items: list[AtlassianItem] = Field(default_factory=list)
    things_tasks: list[ThingsTask] = Field(default_factory=list)
    wakatime_activities: list[WakatimeActivity] = Field(default_factory=list)
    google_docs: list[GoogleDoc] = Field(default_factory=list)
    whoop_recovery: WhoopRecovery | None = None
    whoop_sleep: list[WhoopSleep] = Field(default_factory=list)
    whoop_workouts: list[WhoopWorkout] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
