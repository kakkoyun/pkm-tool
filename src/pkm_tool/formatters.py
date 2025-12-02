"""Output formatters for PKM tool."""

import re
from datetime import date
from pathlib import Path

from pkm_tool.config import DEFAULT_SECTION_ORDER, DEFAULT_SECTION_TITLES, SectionConfig
from pkm_tool.models import AggregatedData


def _get_section_title(section_name: str, section_config: SectionConfig | None) -> str:
    """Get section title from config or default."""
    if section_config and section_name in section_config.titles:
        return section_config.titles[section_name]
    return DEFAULT_SECTION_TITLES.get(section_name, section_name.replace("_", " ").title())


def _get_section_order(section_config: SectionConfig | None) -> list[str]:
    """Get section order from config or default."""
    if section_config:
        return section_config.order
    return DEFAULT_SECTION_ORDER


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
    """Format errors content (without header)."""
    lines: list[str] = []
    errors = {k: v for k, v in data.metadata.items() if k.endswith("_error")}
    for source, error in errors.items():
        source_name = source.replace("_error", "").replace("_", " ").title()
        lines.append(f"- **{source_name}:** {error}")
    return lines


def _has_section_data(data: AggregatedData, section_name: str) -> bool:
    """Check if a section has data to display."""
    if section_name == "calendar_events":
        return bool(data.calendar_events)
    if section_name == "github_activities":
        return bool(data.github_activities)
    if section_name == "atlassian_items":
        return bool(data.atlassian_items)
    if section_name == "things_tasks":
        return bool(data.things_tasks)
    if section_name == "wakatime_activities":
        return bool(data.wakatime_activities)
    if section_name == "google_docs":
        return bool(data.google_docs)
    if section_name == "whoop_data":
        return bool(data.whoop_recovery or data.whoop_sleep or data.whoop_workouts)
    if section_name == "errors":
        return any(k.endswith("_error") for k in data.metadata)
    return False


def _format_section_content(data: AggregatedData, section_name: str) -> list[str]:
    """Get formatted content for a section (without header)."""
    if section_name == "calendar_events":
        return _format_calendar_events_content(data)
    if section_name == "github_activities":
        return _format_github_activities_content(data)
    if section_name == "atlassian_items":
        return _format_atlassian_items_content(data)
    if section_name == "things_tasks":
        return _format_things_tasks_content(data)
    if section_name == "wakatime_activities":
        return _format_wakatime_activities_content(data)
    if section_name == "google_docs":
        return _format_google_docs_content(data)
    if section_name == "whoop_data":
        return _format_whoop_data_content(data)
    if section_name == "errors":
        return _format_errors_content(data)
    return []


def format_as_markdown(data: AggregatedData, section_config: SectionConfig | None = None) -> str:
    """
    Format aggregated data as Markdown.

    Args:
        data: AggregatedData to format
        section_config: Optional section configuration for titles and order

    Returns:
        Markdown string
    """
    lines: list[str] = []

    # Header
    lines.append(f"# Daily Report - {data.date.strftime('%Y-%m-%d')}")
    lines.append("")

    # Format sections in configured order
    section_order = _get_section_order(section_config)
    for section_name in section_order:
        if _has_section_data(data, section_name):
            title = _get_section_title(section_name, section_config)
            lines.append(f"## {title}")
            lines.append("")
            content = _format_section_content(data, section_name)
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

    # Map header text to section identifiers
    if "calendar" in cleaned and "event" in cleaned:
        return "calendar_events"
    if "github" in cleaned:
        return "github_activities"
    if any(word in cleaned for word in ["atlassian", "jira", "confluence"]):
        return "atlassian_items"
    if "things" in cleaned or ("completed" in cleaned and "task" in cleaned):
        return "things_tasks"
    if "wakatime" in cleaned or ("coding" in cleaned and "activity" in cleaned):
        return "wakatime_activities"
    if "google" in cleaned and "docs" in cleaned:
        return "google_docs"
    if "whoop" in cleaned or ("health" in cleaned and "data" in cleaned):
        return "whoop_data"
    if "error" in cleaned:
        return "errors"

    return None


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

    for i, line in enumerate(lines):
        # Check if this is a header line
        if line.startswith("##"):
            section_id = identify_section(line)

            if section_id:
                # This is a PKM section header
                in_preamble = False
                in_postamble = False

                # Save previous PKM section if any
                if current_section:
                    sections[current_section] = "\n".join(current_content)
                    current_content = []

                # Start new PKM section
                current_section = section_id
                current_content = [line]
            else:
                # This is a non-PKM header
                if current_section:
                    # We were in a PKM section, now entering postamble
                    sections[current_section] = "\n".join(current_content)
                    current_section = None
                    current_content = []
                    in_postamble = True
                    sections["_postamble"] = line
                elif in_preamble:
                    # Still in preamble
                    if sections["_preamble"]:
                        sections["_preamble"] += "\n" + line
                    else:
                        sections["_preamble"] = line
                else:
                    # In postamble
                    sections["_postamble"] += "\n" + line
        elif in_postamble:
            # Content in postamble (after PKM sections)
            sections["_postamble"] += "\n" + line
        elif current_section:
            # We're inside a PKM section
            current_content.append(line)
        elif in_preamble:
            # We're in the preamble (before any PKM sections)
            if sections["_preamble"]:
                sections["_preamble"] += "\n" + line
            else:
                sections["_preamble"] = line

    # Save the last PKM section if any
    if current_section and current_content:
        sections[current_section] = "\n".join(current_content)

    return sections


def _format_section(
    data: AggregatedData, section_name: str, section_config: SectionConfig | None = None
) -> str:
    """
    Format a single section from AggregatedData.

    Args:
        data: Aggregated data
        section_name: Section identifier (e.g., "calendar_events")
        section_config: Optional section configuration for titles

    Returns:
        Formatted markdown section
    """
    if not _has_section_data(data, section_name):
        return ""

    lines: list[str] = []
    title = _get_section_title(section_name, section_config)
    lines.append(f"## {title}")
    lines.append("")
    content = _format_section_content(data, section_name)
    lines.extend(content)
    lines.append("")

    return "\n".join(lines).rstrip()


def merge_sections(
    existing: dict[str, str],
    new_data: AggregatedData,
    format: str,
    section_config: SectionConfig | None = None,
) -> str:
    """
    Merge existing file sections with new PKM data.

    - Preserve preamble and postamble (manual content)
    - Replace existing PKM sections with fresh data
    - Append new PKM sections that weren't in file

    Args:
        existing: Parsed sections from existing file
        new_data: New aggregated data
        format: Output format (should be "markdown")
        section_config: Optional section configuration for titles and order

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

    # Get section order from config
    section_order = _get_section_order(section_config)

    # Track which sections have been added
    added_sections: set[str] = set()

    # First, add sections that existed in the original file (to maintain order)
    for section_name in section_order:
        if section_name in existing and section_name not in ["_preamble", "_postamble"]:
            # Replace with fresh data
            section_content = _format_section(new_data, section_name, section_config)
            if section_content:
                lines.append(section_content)
                added_sections.add(section_name)

    # Then add new sections that weren't in the original file
    for section_name in section_order:
        if section_name not in added_sections:
            section_content = _format_section(new_data, section_name, section_config)
            if section_content:
                lines.append(section_content)

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
    section_config: SectionConfig | None = None,
) -> None:
    """
    Write report to file, optionally merging with existing content.

    Args:
        data: Data to write
        output_path: Target file path
        format: "markdown" or "json"
        merge_existing: If True and file exists, merge sections
        section_config: Optional section configuration for titles and order
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
        output = merge_sections(existing, data, format, section_config)
    else:
        output = format_as_markdown(data, section_config)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output)
