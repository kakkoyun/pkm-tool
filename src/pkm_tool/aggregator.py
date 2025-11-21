"""Data aggregation from all sources."""

import time
from datetime import date

import structlog

from pkm_tool.config import Config, SourceConfig, load_config
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


def should_skip_source_for_weekend(
    is_weekend: bool,
    config: Config,
    source_config: SourceConfig,
    exclude_weekends_override: bool | None,
) -> tuple[bool, str | None]:
    """
    Determine whether a source should be skipped for weekend processing.

    Args:
        is_weekend: Whether the target date falls on a weekend
        config: Loaded configuration object
        source_config: Specific source configuration
        exclude_weekends_override: CLI override flag

    Returns:
        Tuple of (should_skip, reason)
    """
    if not is_weekend:
        return False, None

    if exclude_weekends_override is True:
        return True, "cli_override"
    if exclude_weekends_override is False:
        return False, None

    if config.exclude_weekends:
        return True, "global_config"
    if source_config.exclude_weekends:
        return True, "source_config"

    return False, None


def aggregate_data(
    target_date: date,
    config_path: str | None = None,
    exclude_weekends_override: bool | None = None,
    config_obj: Config | None = None,
) -> AggregatedData:
    """
    Aggregate data from all configured sources.

    Args:
        target_date: Date to fetch data for
        config_path: Optional path to configuration file
        exclude_weekends_override: CLI override for weekend exclusion (None to use config)

    Returns:
        AggregatedData containing all fetched information
    """
    logger.info("aggregate_data_started", target_date=str(target_date))
    config = config_obj or load_config(config_path)
    is_weekend = target_date.weekday() >= 5

    data = AggregatedData(date=target_date)

    # Fetch from each source if enabled
    if config.apple_calendar.enabled:
        skip, reason = should_skip_source_for_weekend(
            is_weekend, config, config.apple_calendar, exclude_weekends_override
        )
        if skip:
            logger.info(
                "source_skipped_for_weekend",
                source="apple_calendar",
                target_date=str(target_date),
                reason=reason,
            )
            data.metadata["apple_calendar_skipped"] = f"weekend ({reason})"
        else:
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
        skip, reason = should_skip_source_for_weekend(
            is_weekend, config, config.github, exclude_weekends_override
        )
        if skip:
            logger.info(
                "source_skipped_for_weekend",
                source="github",
                target_date=str(target_date),
                reason=reason,
            )
            data.metadata["github_skipped"] = f"weekend ({reason})"
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
        skip, reason = should_skip_source_for_weekend(
            is_weekend, config, config.atlassian, exclude_weekends_override
        )
        if skip:
            logger.info(
                "source_skipped_for_weekend",
                source="atlassian",
                target_date=str(target_date),
                reason=reason,
            )
            data.metadata["atlassian_skipped"] = f"weekend ({reason})"
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
        skip, reason = should_skip_source_for_weekend(
            is_weekend, config, config.things, exclude_weekends_override
        )
        if skip:
            logger.info(
                "source_skipped_for_weekend",
                source="things",
                target_date=str(target_date),
                reason=reason,
            )
            data.metadata["things_skipped"] = f"weekend ({reason})"
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
        skip, reason = should_skip_source_for_weekend(
            is_weekend, config, config.wakatime, exclude_weekends_override
        )
        if skip:
            logger.info(
                "source_skipped_for_weekend",
                source="wakatime",
                target_date=str(target_date),
                reason=reason,
            )
            data.metadata["wakatime_skipped"] = f"weekend ({reason})"
        else:
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
        skip, reason = should_skip_source_for_weekend(
            is_weekend, config, config.google_docs, exclude_weekends_override
        )
        if skip:
            logger.info(
                "source_skipped_for_weekend",
                source="google_docs",
                target_date=str(target_date),
                reason=reason,
            )
            data.metadata["google_docs_skipped"] = f"weekend ({reason})"
        else:
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

    if config.whoop.enabled:
        skip, reason = should_skip_source_for_weekend(
            is_weekend, config, config.whoop, exclude_weekends_override
        )
        if skip:
            logger.info(
                "source_skipped_for_weekend",
                source="whoop",
                target_date=str(target_date),
                reason=reason,
            )
            data.metadata["whoop_skipped"] = f"weekend ({reason})"
        else:
            logger.info("fetching_source", source="whoop", enabled=True)
            start_time = time.time()
            try:
                data.whoop_recovery = fetch_whoop_recovery(target_date, config.whoop.config)
                recovery_count = 1 if data.whoop_recovery else 0
                data.whoop_sleep = fetch_whoop_sleep(target_date, config.whoop.config)
                data.whoop_workouts = fetch_whoop_workouts(target_date, config.whoop.config)
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
