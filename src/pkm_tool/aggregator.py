"""Data aggregation from all sources."""

import time
from datetime import date

import structlog

from pkm_tool.config import load_config
from pkm_tool.models import AggregatedData
from pkm_tool.sources.apple_calendar import fetch_calendar_events
from pkm_tool.sources.atlassian import fetch_atlassian_items
from pkm_tool.sources.github import fetch_github_activities
from pkm_tool.sources.google_docs import fetch_google_docs
from pkm_tool.sources.things import fetch_things_tasks
from pkm_tool.sources.wakatime import fetch_wakatime_activities

logger = structlog.get_logger(__name__)


def aggregate_data(target_date: date, config_path: str | None = None) -> AggregatedData:
    """
    Aggregate data from all configured sources.

    Args:
        target_date: Date to fetch data for
        config_path: Optional path to configuration file

    Returns:
        AggregatedData containing all fetched information
    """
    logger.info("aggregate_data_started", target_date=str(target_date))
    config = load_config(config_path)

    data = AggregatedData(date=target_date)

    # Fetch from each source if enabled
    if config.apple_calendar.enabled:
        logger.info("fetching_source", source="apple_calendar", enabled=True)
        start_time = time.time()
        try:
            data.calendar_events = fetch_calendar_events(target_date, config.apple_calendar.config)
            duration = time.time() - start_time
            logger.info(
                "source_fetch_completed",
                source="apple_calendar",
                duration_seconds=f"{duration:.2f}",
                items_count=len(data.calendar_events),
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.warning(
                "source_fetch_failed",
                source="apple_calendar",
                error=str(e),
                duration_seconds=f"{duration:.2f}",
                exc_info=True,
            )
            data.metadata["apple_calendar_error"] = str(e)
    else:
        logger.debug("source_disabled", source="apple_calendar")

    if config.github.enabled:
        logger.info("fetching_source", source="github", enabled=True)
        start_time = time.time()
        try:
            data.github_activities = fetch_github_activities(target_date, config.github.config)
            duration = time.time() - start_time
            logger.info(
                "source_fetch_completed",
                source="github",
                duration_seconds=f"{duration:.2f}",
                items_count=len(data.github_activities),
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.warning(
                "source_fetch_failed",
                source="github",
                error=str(e),
                duration_seconds=f"{duration:.2f}",
                exc_info=True,
            )
            data.metadata["github_error"] = str(e)
    else:
        logger.debug("source_disabled", source="github")

    if config.atlassian.enabled:
        logger.info("fetching_source", source="atlassian", enabled=True)
        start_time = time.time()
        try:
            data.atlassian_items = fetch_atlassian_items(target_date, config.atlassian.config)
            duration = time.time() - start_time
            logger.info(
                "source_fetch_completed",
                source="atlassian",
                duration_seconds=f"{duration:.2f}",
                items_count=len(data.atlassian_items),
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.warning(
                "source_fetch_failed",
                source="atlassian",
                error=str(e),
                duration_seconds=f"{duration:.2f}",
                exc_info=True,
            )
            data.metadata["atlassian_error"] = str(e)
    else:
        logger.debug("source_disabled", source="atlassian")

    if config.things.enabled:
        logger.info("fetching_source", source="things", enabled=True)
        start_time = time.time()
        try:
            data.things_tasks = fetch_things_tasks(target_date, config.things.config)
            duration = time.time() - start_time
            logger.info(
                "source_fetch_completed",
                source="things",
                duration_seconds=f"{duration:.2f}",
                items_count=len(data.things_tasks),
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.warning(
                "source_fetch_failed",
                source="things",
                error=str(e),
                duration_seconds=f"{duration:.2f}",
                exc_info=True,
            )
            data.metadata["things_error"] = str(e)
    else:
        logger.debug("source_disabled", source="things")

    if config.wakatime.enabled:
        logger.info("fetching_source", source="wakatime", enabled=True)
        start_time = time.time()
        try:
            data.wakatime_activities = fetch_wakatime_activities(
                target_date, config.wakatime.config
            )
            duration = time.time() - start_time
            logger.info(
                "source_fetch_completed",
                source="wakatime",
                duration_seconds=f"{duration:.2f}",
                items_count=len(data.wakatime_activities),
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.warning(
                "source_fetch_failed",
                source="wakatime",
                error=str(e),
                duration_seconds=f"{duration:.2f}",
                exc_info=True,
            )
            data.metadata["wakatime_error"] = str(e)
    else:
        logger.debug("source_disabled", source="wakatime")

    if config.google_docs.enabled:
        logger.info("fetching_source", source="google_docs", enabled=True)
        start_time = time.time()
        try:
            data.google_docs = fetch_google_docs(target_date, config.google_docs.config)
            duration = time.time() - start_time
            logger.info(
                "source_fetch_completed",
                source="google_docs",
                duration_seconds=f"{duration:.2f}",
                items_count=len(data.google_docs),
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.warning(
                "source_fetch_failed",
                source="google_docs",
                error=str(e),
                duration_seconds=f"{duration:.2f}",
                exc_info=True,
            )
            data.metadata["google_docs_error"] = str(e)
    else:
        logger.debug("source_disabled", source="google_docs")

    logger.info("aggregate_data_completed", target_date=str(target_date))
    return data
