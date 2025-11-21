"""Data aggregation from all sources."""

from datetime import date

from pkm_tool.config import load_config
from pkm_tool.models import AggregatedData
from pkm_tool.sources.apple_calendar import fetch_calendar_events
from pkm_tool.sources.atlassian import fetch_atlassian_items
from pkm_tool.sources.github import fetch_github_activities
from pkm_tool.sources.google_docs import fetch_google_docs
from pkm_tool.sources.things import fetch_things_tasks
from pkm_tool.sources.wakatime import fetch_wakatime_activities


def aggregate_data(target_date: date, config_path: str | None = None) -> AggregatedData:
    """
    Aggregate data from all configured sources.

    Args:
        target_date: Date to fetch data for
        config_path: Optional path to configuration file

    Returns:
        AggregatedData containing all fetched information
    """
    config = load_config(config_path)

    data = AggregatedData(date=target_date)

    # Fetch from each source if enabled
    if config.apple_calendar.enabled:
        try:
            data.calendar_events = fetch_calendar_events(target_date, config.apple_calendar.config)
        except Exception as e:
            data.metadata["apple_calendar_error"] = str(e)

    if config.github.enabled:
        try:
            data.github_activities = fetch_github_activities(target_date, config.github.config)
        except Exception as e:
            data.metadata["github_error"] = str(e)

    if config.atlassian.enabled:
        try:
            data.atlassian_items = fetch_atlassian_items(target_date, config.atlassian.config)
        except Exception as e:
            data.metadata["atlassian_error"] = str(e)

    if config.things.enabled:
        try:
            data.things_tasks = fetch_things_tasks(target_date, config.things.config)
        except Exception as e:
            data.metadata["things_error"] = str(e)

    if config.wakatime.enabled:
        try:
            data.wakatime_activities = fetch_wakatime_activities(
                target_date, config.wakatime.config
            )
        except Exception as e:
            data.metadata["wakatime_error"] = str(e)

    if config.google_docs.enabled:
        try:
            data.google_docs = fetch_google_docs(target_date, config.google_docs.config)
        except Exception as e:
            data.metadata["google_docs_error"] = str(e)

    return data
