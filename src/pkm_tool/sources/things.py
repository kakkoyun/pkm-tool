"""Things app integration."""

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from pkm_tool.models import ThingsTask


def fetch_things_tasks(target_date: date, config: dict[str, Any]) -> list[ThingsTask]:
    """
    Fetch completed tasks from Things logbook.

    Things stores its data in a SQLite database on macOS.

    Args:
        target_date: Date to fetch tasks for
        config: Configuration dictionary with optional 'database_path'

    Returns:
        List of ThingsTask objects
    """
    # Default Things database path on macOS
    default_db_path = (
        Path.home()
        / "Library"
        / "Group Containers"
        / "JLMPQHK86H.com.culturedcode.ThingsMac"
        / "Things Database.thingsdatabase"
        / "main.sqlite"
    )

    db_path = config.get("database_path", str(default_db_path))

    if not Path(db_path).exists():
        return []

    tasks = []

    # Calculate date range
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())

    # Convert to Things timestamp format (seconds since 2001-01-01)
    reference_date = datetime(2001, 1, 1)
    start_timestamp = (start_datetime - reference_date).total_seconds()
    end_timestamp = (end_datetime - reference_date).total_seconds()

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()

        # Query completed tasks
        query = """
        SELECT 
            t.title,
            t.stopDate,
            p.title as project,
            GROUP_CONCAT(tg.title, ',') as tags
        FROM TMTask t
        LEFT JOIN TMTask p ON t.project = p.uuid
        LEFT JOIN TMTaskTag tt ON t.uuid = tt.tasks
        LEFT JOIN TMTag tg ON tt.tags = tg.uuid
        WHERE t.status = 3
        AND t.stopDate >= ?
        AND t.stopDate < ?
        GROUP BY t.uuid
        ORDER BY t.stopDate
        """

        cursor.execute(query, (start_timestamp, end_timestamp))

        for row in cursor.fetchall():
            title, stop_date, project, tags_str = row

            # Convert Things timestamp back to datetime
            completed_datetime = reference_date + timedelta(seconds=stop_date)

            # Parse tags
            tags = [tag.strip() for tag in tags_str.split(",")] if tags_str else []

            task = ThingsTask(
                title=title,
                completed_date=completed_datetime,
                project=project,
                tags=tags,
            )
            tasks.append(task)

        conn.close()
    except (sqlite3.Error, OSError):
        pass

    return tasks
