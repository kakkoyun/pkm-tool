"""Data aggregation from all sources."""

import time
from datetime import date

import structlog

from pkm_tool.config import CacheConfig, load_config
from pkm_tool.models import AggregatedData
from pkm_tool.sources.apple_calendar import fetch_calendar_events
from pkm_tool.sources.atlassian import fetch_atlassian_items
from pkm_tool.sources.github import fetch_github_activities
from pkm_tool.sources.google_docs import fetch_google_docs
from pkm_tool.sources.things import fetch_things_tasks
from pkm_tool.sources.wakatime import fetch_wakatime_activities
from pkm_tool.sources.whoop import (
    fetch_whoop_recovery,
    fetch_whoop_sleep,
    fetch_whoop_workouts,
)

logger = structlog.get_logger(__name__)


def aggregate_data(
    target_date: date, config_path: str | None = None, exclude_weekends_override: bool | None = None
) -> AggregatedData:
    """
    Aggregate data from all configured sources.

    Args:
        target_date: Date to fetch data for
        config_path: Optional path to configuration file
        exclude_weekends_override: If set, overrides per-source config

    Returns:
        AggregatedData containing all fetched information
    """
    logger.info("aggregate_data_started", target_date=str(target_date))
    config = load_config(config_path)

    data = AggregatedData(date=target_date)
    is_weekend = target_date.weekday() >= 5  # Saturday=5, Sunday=6

    # Get cache config for HTTP-based sources
    cache_config: CacheConfig | None = config.cache if config.cache.enabled else None
    if cache_config:
        logger.debug(
            "cache_enabled",
            directory=config.cache.directory,
            ttl_hours=config.cache.ttl_hours,
        )

    # Fetch from each source if enabled
    if config.apple_calendar.enabled:
        # Check weekend exclusion
        skip_weekend = (
            exclude_weekends_override
            if exclude_weekends_override is not None
            else config.apple_calendar.exclude_weekends
        )
        if is_weekend and skip_weekend:
            logger.info("source_skipped_weekend", source="apple_calendar")
        else:
            logger.info("fetching_source", source="apple_calendar", enabled=True)
            start_time = time.time()
            try:
                data.calendar_events = fetch_calendar_events(
                    target_date, config.apple_calendar.config
                )
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
        # Check weekend exclusion
        skip_weekend = (
            exclude_weekends_override
            if exclude_weekends_override is not None
            else config.github.exclude_weekends
        )
        if is_weekend and skip_weekend:
            logger.info("source_skipped_weekend", source="github")
        else:
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
        # Check weekend exclusion
        skip_weekend = (
            exclude_weekends_override
            if exclude_weekends_override is not None
            else config.atlassian.exclude_weekends
        )
        if is_weekend and skip_weekend:
            logger.info("source_skipped_weekend", source="atlassian")
        else:
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
        # Check weekend exclusion
        skip_weekend = (
            exclude_weekends_override
            if exclude_weekends_override is not None
            else config.things.exclude_weekends
        )
        if is_weekend and skip_weekend:
            logger.info("source_skipped_weekend", source="things")
        else:
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
        # Check weekend exclusion
        skip_weekend = (
            exclude_weekends_override
            if exclude_weekends_override is not None
            else config.wakatime.exclude_weekends
        )
        if is_weekend and skip_weekend:
            logger.info("source_skipped_weekend", source="wakatime")
        else:
            logger.info("fetching_source", source="wakatime", enabled=True)
            start_time = time.time()
            try:
                data.wakatime_activities = fetch_wakatime_activities(
                    target_date, config.wakatime.config, cache_config
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
        # Check weekend exclusion
        skip_weekend = (
            exclude_weekends_override
            if exclude_weekends_override is not None
            else config.google_docs.exclude_weekends
        )
        if is_weekend and skip_weekend:
            logger.info("source_skipped_weekend", source="google_docs")
        else:
            logger.info("fetching_source", source="google_docs", enabled=True)
            start_time = time.time()
            try:
                data.google_docs = fetch_google_docs(
                    target_date, config.google_docs.config, cache_config
                )
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

    if config.whoop.enabled:
        # Check weekend exclusion
        skip_weekend = (
            exclude_weekends_override
            if exclude_weekends_override is not None
            else config.whoop.exclude_weekends
        )
        if is_weekend and skip_weekend:
            logger.info("source_skipped_weekend", source="whoop")
        else:
            logger.info("fetching_source", source="whoop", enabled=True)
            start_time = time.time()
            try:
                # Fetch recovery data (single entry per day)
                data.whoop_recovery = fetch_whoop_recovery(
                    target_date, config.whoop.config, cache_config
                )
                recovery_count = 1 if data.whoop_recovery else 0

                # Fetch sleep cycles (can be multiple per day)
                data.whoop_sleep = fetch_whoop_sleep(target_date, config.whoop.config, cache_config)

                # Fetch workouts (can be multiple per day)
                data.whoop_workouts = fetch_whoop_workouts(
                    target_date, config.whoop.config, cache_config
                )

                total_items = recovery_count + len(data.whoop_sleep) + len(data.whoop_workouts)
                duration = time.time() - start_time
                logger.info(
                    "source_fetch_completed",
                    source="whoop",
                    duration_seconds=f"{duration:.2f}",
                    items_count=total_items,
                    recovery_count=recovery_count,
                    sleep_count=len(data.whoop_sleep),
                    workout_count=len(data.whoop_workouts),
                )
            except Exception as e:
                duration = time.time() - start_time
                logger.warning(
                    "source_fetch_failed",
                    source="whoop",
                    error=str(e),
                    duration_seconds=f"{duration:.2f}",
                    exc_info=True,
                )
                data.metadata["whoop_error"] = str(e)
    else:
        logger.debug("source_disabled", source="whoop")

    logger.info("aggregate_data_completed", target_date=str(target_date))
    return data
