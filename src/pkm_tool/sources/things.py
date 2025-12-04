"""Things app integration."""

import platform
from datetime import date, datetime
from typing import Any

import structlog

from pkm_tool.models import ThingsTask

logger = structlog.get_logger(__name__)


def fetch_things_tasks(target_date: date, config: dict[str, Any]) -> list[ThingsTask]:
    """
    Fetch completed tasks from Things logbook using things-py library.

    Args:
        target_date: Date to fetch tasks for
        config: Configuration dictionary (currently unused, kept for interface compatibility)

    Returns:
        List of ThingsTask objects (empty list on error or non-macOS)
    """
    logger.debug("things_fetch_started", date=str(target_date))

    # Check if running on macOS
    if platform.system() != "Darwin":
        logger.debug("things_not_macos", message="Things only available on macOS")
        return []

    try:
        tasks = _fetch_things_via_library(target_date)
        logger.info("things_tasks_fetched", task_count=len(tasks))
        return tasks
    except Exception as e:
        # Handle all errors at top level for consistent error reporting
        logger.error("things_fetch_failed", error=str(e), exc_info=True)
        return []


def _fetch_things_via_library(target_date: date) -> list[ThingsTask]:
    """
    Internal implementation using things-py library.

    Args:
        target_date: Date to fetch tasks for

    Returns:
        List of ThingsTask objects completed on target_date
    """
    import things  # Import here to avoid issues on non-macOS platforms

    # Fetch all completed tasks
    completed_tasks = things.todos(status="completed")

    # Filter by target date and convert to ThingsTask models
    tasks = []
    for task in completed_tasks:
        # Parse stop_date string to datetime
        stop_date_str = task.get("stop_date")
        if not stop_date_str:
            continue

        # Parse the stop_date string (format: "YYYY-MM-DD HH:MM:SS")
        try:
            completed_datetime = datetime.strptime(stop_date_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            continue

        # Filter by date
        if completed_datetime.date() != target_date:
            continue

        # Extract project title (not project uuid)
        project = task.get("project_title")

        # Extract tags (handle None case)
        tags = task.get("tags", [])
        if tags is None:
            tags = []

        # Create ThingsTask model
        title = task.get("title")
        if not title:
            continue
        things_task = ThingsTask(
            title=title,
            completed_date=completed_datetime,
            project=project,
            tags=tags,
        )
        tasks.append(things_task)

    # Sort by completion time
    tasks.sort(key=lambda t: t.completed_date)

    return tasks
