"""Output formatters for PKM tool."""

import re
from datetime import date
from pathlib import Path
from typing import Any

from pkm_tool.config import DEFAULT_SOURCE_TITLES, ERRORS_TITLE, Config
from pkm_tool.models import AggregatedData

# Mapping from source name to data field name
SOURCE_TO_DATA_FIELD: dict[str, str] = {
    "apple_calendar": "calendar_events",
    "github": "github_activities",
    "atlassian": "atlassian_items",
    "things": "things_tasks",
    "wakatime": "wakatime_activities",
    "google_docs": "google_docs",
    "whoop": "whoop_data",
}


def format_as_json(data: AggregatedData) -> str:
    """
    Format aggregated data as JSON.

    Args:
        data: AggregatedData to format

    Returns:
        JSON string
    """
    return data.model_dump_json(indent=2)


def _format_calendar_events_content(data: AggregatedData) -> list[str]:
    """Format calendar events content (without header)."""
    lines: list[str] = []
    for event in sorted(data.calendar_events, key=lambda e: e.start):
        time_str = f"{event.start.strftime('%H:%M')} - {event.end.strftime('%H:%M')}"
        lines.append(f"- **{time_str}** {event.title}")
        if event.location:
            lines.append(f"  - Location: {event.location}")
        if event.description:
            lines.append(f"  - {event.description}")
    return lines


def _format_github_activities_content(data: AggregatedData) -> list[str]:
    """Format GitHub activities content (without header)."""
    lines: list[str] = []
    for activity in sorted(data.github_activities, key=lambda a: a.timestamp):
        time_str = activity.timestamp.strftime("%H:%M")
        icon = {"commit": "📝", "pr": "🔀", "issue": "📋", "review": "👁️"}.get(activity.type, "•")
        link_text = f"[{activity.repository}]({activity.url})"
        lines.append(f"- {icon} **{time_str}** {link_text} - {activity.title}")
        if activity.details:
            lines.append(f"  - {activity.details}")
    return lines


def _format_atlassian_items_content(data: AggregatedData) -> list[str]:
    """Format Atlassian items content (without header)."""
    lines: list[str] = []
    for item in sorted(data.atlassian_items, key=lambda i: i.updated):
        icon = "📋" if item.type == "jira_issue" else "📄"
        status_str = f" ({item.status})" if item.status else ""
        lines.append(f"- {icon} [{item.key}]({item.url}) - {item.title}{status_str}")
    return lines


def _format_things_tasks_content(data: AggregatedData) -> list[str]:
    """Format Things tasks content (without header)."""
    lines: list[str] = []
    for task in sorted(data.things_tasks, key=lambda t: t.completed_date):
        time_str = task.completed_date.strftime("%H:%M")
        project_str = f" ({task.project})" if task.project else ""
        tags_str = f" #{', #'.join(task.tags)}" if task.tags else ""
        lines.append(f"- **{time_str}** {task.title}{project_str}{tags_str}")
    return lines


def _format_wakatime_activities_content(data: AggregatedData) -> list[str]:
    """Format Wakatime activities content (without header)."""
    lines: list[str] = []
    total_seconds = sum(a.duration_seconds for a in data.wakatime_activities)
    total_hours = total_seconds / 3600
    lines.append(f"**Total Time:** {total_hours:.2f} hours")
    lines.append("")
    sorted_activities = sorted(
        data.wakatime_activities, key=lambda a: a.duration_seconds, reverse=True
    )
    for activity in sorted_activities:
        hours = activity.duration_seconds / 3600
        lang_str = f" ({activity.language})" if activity.language else ""
        lines.append(f"- {activity.project}{lang_str}: {hours:.2f}h")
    return lines


def _format_google_docs_content(data: AggregatedData) -> list[str]:
    """Format Google Docs content (without header)."""
    lines: list[str] = []
    for doc in sorted(data.google_docs, key=lambda d: d.opened_at):
        time_str = doc.opened_at.strftime("%H:%M")
        lines.append(f"- **{time_str}** [{doc.title}]({doc.url})")
    return lines


def _format_whoop_data_content(data: AggregatedData) -> list[str]:
    """Format Whoop health data content (without header)."""
    lines: list[str] = []

    # Recovery
    if data.whoop_recovery:
        recovery = data.whoop_recovery
        lines.append(
            f"**Recovery:** {recovery.recovery_score:.0f}% "
            f"(HRV: {recovery.hrv:.0f}ms, Resting HR: {recovery.resting_heart_rate} bpm)"
        )
        lines.append("")

    # Sleep
    if data.whoop_sleep:
        lines.append("**Sleep:**")
        for sleep in sorted(data.whoop_sleep, key=lambda s: s.start):
            start_str = sleep.start.strftime("%H:%M")
            end_str = sleep.end.strftime("%H:%M")
            hours = sleep.duration_minutes // 60
            mins = sleep.duration_minutes % 60
            efficiency_str = (
                f" - {sleep.sleep_efficiency:.0f}% efficiency" if sleep.sleep_efficiency else ""
            )
            lines.append(f"- {start_str} - {end_str} ({hours}h {mins}m){efficiency_str}")

            # Sleep stages
            stages = []
            if sleep.deep_sleep_minutes:
                deep_h = sleep.deep_sleep_minutes // 60
                deep_m = sleep.deep_sleep_minutes % 60
                stages.append(f"Deep: {deep_h}h {deep_m}m")
            if sleep.light_sleep_minutes:
                light_h = sleep.light_sleep_minutes // 60
                light_m = sleep.light_sleep_minutes % 60
                stages.append(f"Light: {light_h}h {light_m}m")
            if sleep.rem_sleep_minutes:
                rem_h = sleep.rem_sleep_minutes // 60
                rem_m = sleep.rem_sleep_minutes % 60
                stages.append(f"REM: {rem_h}h {rem_m}m")
            if stages:
                lines.append(f"  - {', '.join(stages)}")
        lines.append("")

    # Workouts
    if data.whoop_workouts:
        lines.append("**Workouts:**")
        for workout in sorted(data.whoop_workouts, key=lambda w: w.start):
            time_str = workout.start.strftime("%H:%M")
            hours = workout.duration_minutes // 60
            mins = workout.duration_minutes % 60
            duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

            strain_str = f"Strain: {workout.strain:.1f}"
            hr_str = (
                f", Avg HR: {workout.average_heart_rate} bpm" if workout.average_heart_rate else ""
            )

            lines.append(
                f"- **{time_str}** {workout.sport_name} ({duration_str}) - {strain_str}{hr_str}"
            )

    return lines


def _format_errors_content(data: AggregatedData) -> list[str]:
    """Format errors content (without header), in folded/details format."""
    lines: list[str] = []
    errors = {k: v for k, v in data.metadata.items() if k.endswith("_error")}
    if errors:
        lines.append("<details>")
        lines.append("<summary>Click to expand errors</summary>")
        lines.append("")
        for source, error in errors.items():
            source_name = source.replace("_error", "").replace("_", " ").title()
            lines.append(f"- **{source_name}:** {error}")
        lines.append("")
        lines.append("</details>")
    return lines


def _has_source_data(data: AggregatedData, source_name: str) -> bool:
    """Check if a source has data to display."""
    # Map source names to data checking functions
    data_checkers: dict[str, Any] = {
        "apple_calendar": lambda d: bool(d.calendar_events),
        "github": lambda d: bool(d.github_activities),
        "atlassian": lambda d: bool(d.atlassian_items),
        "things": lambda d: bool(d.things_tasks),
        "wakatime": lambda d: bool(d.wakatime_activities),
        "google_docs": lambda d: bool(d.google_docs),
        "whoop": lambda d: bool(d.whoop_recovery or d.whoop_sleep or d.whoop_workouts),
    }
    checker = data_checkers.get(source_name)
    return checker(data) if checker else False


def _format_source_content(data: AggregatedData, source_name: str) -> list[str]:
    """Get formatted content for a source (without header)."""
    # Map source names to formatting functions
    content_formatters: dict[str, Any] = {
        "apple_calendar": _format_calendar_events_content,
        "github": _format_github_activities_content,
        "atlassian": _format_atlassian_items_content,
        "things": _format_things_tasks_content,
        "wakatime": _format_wakatime_activities_content,
        "google_docs": _format_google_docs_content,
        "whoop": _format_whoop_data_content,
    }
    formatter = content_formatters.get(source_name)
    return formatter(data) if formatter else []


def _has_errors(data: AggregatedData) -> bool:
    """Check if there are any errors in the data."""
    return any(k.endswith("_error") for k in data.metadata)


def format_as_markdown(data: AggregatedData, config: Config | None = None) -> str:
    """
    Format aggregated data as Markdown.

    Args:
        data: AggregatedData to format
        config: Optional Config for titles and order

    Returns:
        Markdown string
    """
    lines: list[str] = []

    # Header
    lines.append(f"# Daily Report - {data.date.strftime('%Y-%m-%d')}")
    lines.append("")

    # Get ordered sources from config or use default order
    if config:
        source_order = config.get_ordered_sources()
    else:
        source_order = [
            "apple_calendar",
            "github",
            "atlassian",
            "things",
            "wakatime",
            "google_docs",
            "whoop",
        ]

    # Format sources in order
    for source_name in source_order:
        if _has_source_data(data, source_name):
            if config:
                title = config.get_source_title(source_name)
            else:
                title = DEFAULT_SOURCE_TITLES.get(
                    source_name, source_name.replace("_", " ").title()
                )
            lines.append(f"## {title}")
            lines.append("")
            content = _format_source_content(data, source_name)
            lines.extend(content)
            lines.append("")

    # Errors always last, in folded format
    if _has_errors(data):
        lines.append(f"## {ERRORS_TITLE}")
        lines.append("")
        content = _format_errors_content(data)
        lines.extend(content)
        lines.append("")

    return "\n".join(lines)


def format_filename(template: str, target_date: date, output_format: str) -> str:
    """
    Format filename using template and date variables.

    Args:
        template: Filename template with {variables}
        target_date: Date to format
        output_format: "markdown" or "json"

    Returns:
        Formatted filename string
    """
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    format_ext = "md" if output_format == "markdown" else "json"

    replacements = {
        "date": target_date.strftime("%Y-%m-%d"),
        "year": target_date.strftime("%Y"),
        "month": target_date.strftime("%m"),
        "day": target_date.strftime("%d"),
        "day_abbr": day_names[target_date.weekday()],
        "format": format_ext,
    }

    return template.format(**replacements)


def identify_section(header: str) -> str | None:
    """
    Identify PKM section type from header text (case-insensitive, ignore emojis).

    Args:
        header: Header text (e.g., "## 📅 Calendar Events")

    Returns:
        Section identifier or None if not a recognized PKM section
    """
    # Remove emojis and markdown header markers, normalize whitespace
    cleaned = re.sub(r"[#\s]", " ", header)
    cleaned = re.sub(r"[^\w\s-]", "", cleaned)
    cleaned = cleaned.strip().lower()

    # Map keywords to section identifiers (order matters - check specific patterns first)
    section_patterns: list[tuple[str, list[list[str]]]] = [
        ("calendar_events", [["calendar", "event"]]),
        ("github_activities", [["github"]]),
        ("atlassian_items", [["atlassian"], ["jira"], ["confluence"]]),
        ("things_tasks", [["things"], ["completed", "task"]]),
        ("wakatime_activities", [["wakatime"], ["coding", "activity"]]),
        ("google_docs", [["google", "docs"]]),
        ("whoop_data", [["whoop"], ["health", "data"]]),
        ("errors", [["error"]]),
    ]

    for section_id, patterns in section_patterns:
        for pattern in patterns:
            if all(word in cleaned for word in pattern):
                return section_id

    return None


def _append_to_section(sections: dict[str, str], key: str, line: str) -> None:
    """Helper to append a line to a section, handling empty initial state."""
    if sections[key]:
        sections[key] += "\n" + line
    else:
        sections[key] = line


def _save_current_section(
    sections: dict[str, str], current_section: str | None, current_content: list[str]
) -> None:
    """Helper to save the current PKM section content."""
    if current_section and current_content:
        sections[current_section] = "\n".join(current_content)


def _handle_pkm_header(
    line: str,
    section_id: str,
    sections: dict[str, str],
    current_section: str | None,
    current_content: list[str],
) -> tuple[str, list[str], bool, bool]:
    """Handle a PKM section header, return new state."""
    # Save previous PKM section if any
    _save_current_section(sections, current_section, current_content)

    # Start new PKM section
    return section_id, [line], False, False


def _handle_non_pkm_header(
    line: str,
    sections: dict[str, str],
    current_section: str | None,
    current_content: list[str],
    in_preamble: bool,
) -> tuple[str | None, list[str], bool, bool]:
    """Handle a non-PKM header, return new state."""
    if current_section:
        # We were in a PKM section, now entering postamble
        _save_current_section(sections, current_section, current_content)
        sections["_postamble"] = line
        return None, [], in_preamble, True

    if in_preamble:
        # Still in preamble
        _append_to_section(sections, "_preamble", line)
    else:
        # In postamble
        _append_to_section(sections, "_postamble", line)

    return current_section, current_content, in_preamble, in_preamble or True


def parse_existing_file(file_path: Path) -> dict[str, str]:
    """
    Parse existing markdown file and extract sections.

    Returns dict mapping section names to content:
    {
        "_preamble": "Content before first PKM section",
        "calendar_events": "Calendar section content",
        "_postamble": "Content after last PKM section"
    }
    """
    if not file_path.exists():
        return {"_preamble": "", "_postamble": ""}

    content = file_path.read_text()
    lines = content.split("\n")

    sections: dict[str, str] = {"_preamble": "", "_postamble": ""}
    current_section: str | None = None
    current_content: list[str] = []
    in_preamble = True
    in_postamble = False

    for line in lines:
        # Handle header lines
        if line.startswith("##"):
            section_id = identify_section(line)

            if section_id:
                # This is a PKM section header
                current_section, current_content, in_preamble, in_postamble = _handle_pkm_header(
                    line, section_id, sections, current_section, current_content
                )
            else:
                # This is a non-PKM header
                (
                    current_section,
                    current_content,
                    in_preamble,
                    in_postamble,
                ) = _handle_non_pkm_header(
                    line, sections, current_section, current_content, in_preamble
                )
            continue

        # Handle content lines based on current state
        if in_postamble:
            _append_to_section(sections, "_postamble", line)
        elif current_section:
            current_content.append(line)
        elif in_preamble:
            _append_to_section(sections, "_preamble", line)

    # Save the last PKM section if any
    _save_current_section(sections, current_section, current_content)

    return sections


def _format_section(data: AggregatedData, source_name: str, config: Config | None = None) -> str:
    """
    Format a single section from AggregatedData.

    Args:
        data: Aggregated data
        source_name: Source identifier (e.g., "github", "apple_calendar")
        config: Optional config for titles

    Returns:
        Formatted markdown section
    """
    if not _has_source_data(data, source_name):
        return ""

    lines: list[str] = []
    if config:
        title = config.get_source_title(source_name)
    else:
        title = DEFAULT_SOURCE_TITLES.get(source_name, source_name.replace("_", " ").title())
    lines.append(f"## {title}")
    lines.append("")
    content = _format_source_content(data, source_name)
    lines.extend(content)
    lines.append("")

    return "\n".join(lines).rstrip()


def _format_errors_section(data: AggregatedData) -> str:
    """Format the errors section."""
    if not _has_errors(data):
        return ""

    lines: list[str] = []
    lines.append(f"## {ERRORS_TITLE}")
    lines.append("")
    content = _format_errors_content(data)
    lines.extend(content)
    lines.append("")

    return "\n".join(lines).rstrip()


def merge_sections(
    existing: dict[str, str],
    new_data: AggregatedData,
    format: str,
    config: Config | None = None,
) -> str:
    """
    Merge existing file sections with new PKM data.

    - Preserve preamble and postamble (manual content)
    - Replace existing PKM sections with fresh data
    - Append new PKM sections that weren't in file
    - Errors are always last

    Args:
        existing: Parsed sections from existing file
        new_data: New aggregated data
        format: Output format (should be "markdown")
        config: Optional config for titles and order

    Returns:
        Merged markdown content
    """
    lines: list[str] = []

    # Start with preamble (manual content before PKM sections)
    if existing.get("_preamble"):
        preamble = existing["_preamble"].rstrip()
        if preamble:
            lines.append(preamble)
            lines.append("")

    # Get source order from config
    if config:
        source_order = config.get_ordered_sources()
    else:
        source_order = [
            "apple_calendar",
            "github",
            "atlassian",
            "things",
            "wakatime",
            "google_docs",
            "whoop",
        ]

    # Track which sources have been added
    added_sources: set[str] = set()

    # Map from data field names to source names (used by identify_section)
    section_to_source = {
        "calendar_events": "apple_calendar",
        "github_activities": "github",
        "atlassian_items": "atlassian",
        "things_tasks": "things",
        "wakatime_activities": "wakatime",
        "google_docs": "google_docs",
        "whoop_data": "whoop",
    }

    # First, add sections that existed in the original file (to maintain order)
    for source_name in source_order:
        # Check if this source was in the existing file (using old section names)
        old_section_name = None
        for old_name, new_name in section_to_source.items():
            if new_name == source_name and old_name in existing:
                old_section_name = old_name
                break

        if old_section_name and old_section_name not in ["_preamble", "_postamble"]:
            # Replace with fresh data
            section_content = _format_section(new_data, source_name, config)
            if section_content:
                lines.append(section_content)
                added_sources.add(source_name)

    # Then add new sections that weren't in the original file
    for source_name in source_order:
        if source_name not in added_sources:
            section_content = _format_section(new_data, source_name, config)
            if section_content:
                lines.append(section_content)

    # Errors always last
    errors_content = _format_errors_section(new_data)
    if errors_content:
        lines.append(errors_content)

    # End with postamble (manual content after PKM sections)
    if existing.get("_postamble"):
        postamble = existing["_postamble"].strip()
        if postamble:
            # Ensure blank line before postamble
            if lines and lines[-1]:
                lines.append("")
            lines.append(postamble)

    return "\n".join(lines)


def write_report_to_file(
    data: AggregatedData,
    output_path: Path,
    format: str,
    merge_existing: bool = True,
    config: Config | None = None,
) -> None:
    """
    Write report to file, optionally merging with existing content.

    Args:
        data: Data to write
        output_path: Target file path
        format: "markdown" or "json"
        merge_existing: If True and file exists, merge sections
        config: Optional config for titles and order
    """
    if format == "json":
        # JSON mode: always overwrite
        output = format_as_json(data)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output)
        return

    # Markdown mode: smart merge if file exists
    if merge_existing and output_path.exists():
        existing = parse_existing_file(output_path)
        output = merge_sections(existing, data, format, config)
    else:
        output = format_as_markdown(data, config)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output)
