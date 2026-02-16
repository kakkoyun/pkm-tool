"""Data aggregation from all sources."""

import time
from collections.abc import Callable
from datetime import date
from typing import Any

import structlog

from pkm_tool.config import CacheConfig, SourceConfig, load_config
from pkm_tool.exceptions import SourceError
from pkm_tool.logging import bind_correlation_id
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


def _fetch_from_source(
    source_name: str,
    source_config: SourceConfig,
    target_date: date,
    data: AggregatedData,
    fetch_func: Callable[..., Any],
    is_weekend: bool,
    exclude_weekends_override: bool | None,
    result_setter: Callable[[AggregatedData, Any], None],
    cache_config: CacheConfig | None = None,
) -> None:
    """
    Generic helper to fetch data from a source with weekend exclusion, timing, and error handling.

    This centralizes the repetitive pattern used for each source in aggregate_data.

    Args:
        source_name: Name of the source (e.g., "github", "wakatime")
        source_config: SourceConfig for this source
        target_date: Date to fetch data for
        data: AggregatedData object to populate
        fetch_func: Function to call to fetch data
        is_weekend: Whether target_date is a weekend
        exclude_weekends_override: Global override for weekend exclusion
        result_setter: Function to set the result on the data object
        cache_config: Optional cache config for HTTP-based sources
    """
    if not source_config.enabled:
        logger.debug("source_disabled", source=source_name)
        return

    # Check weekend exclusion
    skip_weekend = (
        exclude_weekends_override
        if exclude_weekends_override is not None
        else source_config.exclude_weekends
    )
    if is_weekend and skip_weekend:
        logger.info("source_skipped_weekend", source=source_name)
        return

    logger.info("fetching_source", source=source_name, enabled=True)
    start_time = time.time()
    try:
        # Call fetch function with or without cache_config based on whether it's provided
        if cache_config is not None:
            result = fetch_func(target_date, source_config.config, cache_config)
        else:
            result = fetch_func(target_date, source_config.config)

        duration = time.time() - start_time
        result_setter(data, result)
        # Get count - handle both list results and single object results
        if isinstance(result, list):
            count = len(result)
        elif result is None:
            count = 0
        else:
            count = 1
        logger.info(
            "source_fetch_completed",
            source=source_name,
            duration_seconds=f"{duration:.2f}",
            items_count=count,
        )
    except SourceError as e:
        duration = time.time() - start_time
        logger.warning(
            "source_fetch_failed",
            source=source_name,
            error=str(e),
            retriable=e.retriable,
            duration_seconds=f"{duration:.2f}",
            exc_info=True,
        )
        data.metadata[f"{source_name}_error"] = str(e)
        data.metadata[f"{source_name}_retriable"] = e.retriable
    except Exception as e:
        duration = time.time() - start_time
        logger.warning(
            "source_fetch_failed",
            source=source_name,
            error=str(e),
            duration_seconds=f"{duration:.2f}",
            exc_info=True,
        )
        data.metadata[f"{source_name}_error"] = str(e)


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
    bind_correlation_id()
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

    # Fetch from each source using the common helper
    _fetch_from_source(
        "apple_calendar",
        config.apple_calendar,
        target_date,
        data,
        fetch_calendar_events,
        is_weekend,
        exclude_weekends_override,
        lambda d, result: setattr(d, "calendar_events", result),
    )

    _fetch_from_source(
        "github",
        config.github,
        target_date,
        data,
        fetch_github_activities,
        is_weekend,
        exclude_weekends_override,
        lambda d, result: setattr(d, "github_activities", result),
    )

    _fetch_from_source(
        "atlassian",
        config.atlassian,
        target_date,
        data,
        fetch_atlassian_items,
        is_weekend,
        exclude_weekends_override,
        lambda d, result: setattr(d, "atlassian_items", result),
    )

    _fetch_from_source(
        "things",
        config.things,
        target_date,
        data,
        fetch_things_tasks,
        is_weekend,
        exclude_weekends_override,
        lambda d, result: setattr(d, "things_tasks", result),
    )

    _fetch_from_source(
        "wakatime",
        config.wakatime,
        target_date,
        data,
        fetch_wakatime_activities,
        is_weekend,
        exclude_weekends_override,
        lambda d, result: setattr(d, "wakatime_activities", result),
        cache_config=cache_config,
    )

    _fetch_from_source(
        "google_docs",
        config.google_docs,
        target_date,
        data,
        fetch_google_docs,
        is_weekend,
        exclude_weekends_override,
        lambda d, result: setattr(d, "google_docs", result),
        cache_config=cache_config,
    )

    # Whoop endpoints each get independent error handling via _fetch_from_source
    _fetch_from_source(
        "whoop_recovery",
        config.whoop,
        target_date,
        data,
        fetch_whoop_recovery,
        is_weekend,
        exclude_weekends_override,
        lambda d, result: setattr(d, "whoop_recovery", result),
        cache_config=cache_config,
    )

    _fetch_from_source(
        "whoop_sleep",
        config.whoop,
        target_date,
        data,
        fetch_whoop_sleep,
        is_weekend,
        exclude_weekends_override,
        lambda d, result: setattr(d, "whoop_sleep", result),
        cache_config=cache_config,
    )

    _fetch_from_source(
        "whoop_workouts",
        config.whoop,
        target_date,
        data,
        fetch_whoop_workouts,
        is_weekend,
        exclude_weekends_override,
        lambda d, result: setattr(d, "whoop_workouts", result),
        cache_config=cache_config,
    )

    logger.info("aggregate_data_completed", target_date=str(target_date))
    return data
