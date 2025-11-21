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


class AggregatedData(BaseModel):
    """Aggregated data from all sources."""

    date: date
    calendar_events: list[Event] = Field(default_factory=list)
    github_activities: list[GitHubActivity] = Field(default_factory=list)
    atlassian_items: list[AtlassianItem] = Field(default_factory=list)
    things_tasks: list[ThingsTask] = Field(default_factory=list)
    wakatime_activities: list[WakatimeActivity] = Field(default_factory=list)
    google_docs: list[GoogleDoc] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
