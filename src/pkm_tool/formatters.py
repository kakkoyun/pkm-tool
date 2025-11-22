"""Output formatters for PKM tool."""

import re
from datetime import date
from pathlib import Path

from pkm_tool.models import AggregatedData


def format_as_json(data: AggregatedData) -> str:
    """
    Format aggregated data as JSON.

    Args:
        data: AggregatedData to format

    Returns:
        JSON string
    """
    return data.model_dump_json(indent=2)


def format_as_markdown(data: AggregatedData) -> str:
    """
    Format aggregated data as Markdown.

    Args:
        data: AggregatedData to format

    Returns:
        Markdown string
    """
    lines = []

    # Header
    lines.append(f"# Daily Report - {data.date.strftime('%Y-%m-%d')}")
    lines.append("")

    # Calendar Events
    if data.calendar_events:
        lines.append("## 📅 Calendar Events")
        lines.append("")
        for event in sorted(data.calendar_events, key=lambda e: e.start):
            time_str = f"{event.start.strftime('%H:%M')} - {event.end.strftime('%H:%M')}"
            lines.append(f"- **{time_str}** {event.title}")
            if event.location:
                lines.append(f"  - Location: {event.location}")
            if event.description:
                lines.append(f"  - {event.description}")
        lines.append("")

    # GitHub Activities
    if data.github_activities:
        lines.append("## 🐙 GitHub Activities")
        lines.append("")
        for activity in sorted(data.github_activities, key=lambda a: a.timestamp):
            time_str = activity.timestamp.strftime("%H:%M")
            icon = {"commit": "📝", "pr": "🔀", "issue": "📋", "review": "👁️"}.get(
                activity.type, "•"
            )
            link_text = f"[{activity.repository}]({activity.url})"
            lines.append(f"- {icon} **{time_str}** {link_text} - {activity.title}")
            if activity.details:
                lines.append(f"  - {activity.details}")
        lines.append("")

    # Atlassian Items
    if data.atlassian_items:
        lines.append("## 🏢 Atlassian (Jira/Confluence)")
        lines.append("")
        for item in sorted(data.atlassian_items, key=lambda i: i.updated):
            icon = "📋" if item.type == "jira_issue" else "📄"
            status_str = f" ({item.status})" if item.status else ""
            lines.append(f"- {icon} [{item.key}]({item.url}) - {item.title}{status_str}")
        lines.append("")

    # Things Tasks
    if data.things_tasks:
        lines.append("## ✅ Things - Completed Tasks")
        lines.append("")
        for task in sorted(data.things_tasks, key=lambda t: t.completed_date):
            time_str = task.completed_date.strftime("%H:%M")
            project_str = f" ({task.project})" if task.project else ""
            tags_str = f" #{', #'.join(task.tags)}" if task.tags else ""
            lines.append(f"- **{time_str}** {task.title}{project_str}{tags_str}")
        lines.append("")

    # Wakatime Activities
    if data.wakatime_activities:
        lines.append("## ⏱️ Wakatime - Coding Activity")
        lines.append("")
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
        lines.append("")

    # Google Docs
    if data.google_docs:
        lines.append("## 📝 Google Docs")
        lines.append("")
        for doc in sorted(data.google_docs, key=lambda d: d.opened_at):
            time_str = doc.opened_at.strftime("%H:%M")
            lines.append(f"- **{time_str}** [{doc.title}]({doc.url})")
        lines.append("")

    # Whoop Health Data
    if data.whoop_recovery or data.whoop_sleep or data.whoop_workouts:
        lines.append("## 💪 Whoop Health Data")
        lines.append("")

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
                    f", Avg HR: {workout.average_heart_rate} bpm"
                    if workout.average_heart_rate
                    else ""
                )

                lines.append(
                    f"- **{time_str}** {workout.sport_name} ({duration_str}) - {strain_str}{hr_str}"
                )
            lines.append("")

    # Errors
    errors = {k: v for k, v in data.metadata.items() if k.endswith("_error")}
    if errors:
        lines.append("## ⚠️ Errors")
        lines.append("")
        for source, error in errors.items():
            source_name = source.replace("_error", "").replace("_", " ").title()
            lines.append(f"- **{source_name}:** {error}")
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
    if "things" in cleaned or "completed" in cleaned and "task" in cleaned:
        return "things_tasks"
    if "wakatime" in cleaned or "coding" in cleaned and "activity" in cleaned:
        return "wakatime_activities"
    if "google" in cleaned and "docs" in cleaned:
        return "google_docs"
    if "whoop" in cleaned or "health" in cleaned and "data" in cleaned:
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
    last_pkm_section_end = 0

    for i, line in enumerate(lines):
        # Check if this is a header line
        if line.startswith("##"):
            section_id = identify_section(line)

            if section_id:
                # Save previous section if any
                if current_section:
                    sections[current_section] = "\n".join(current_content)
                    current_content = []

                # Start new PKM section
                current_section = section_id
                current_content = [line]
                last_pkm_section_end = i
            elif current_section:
                # This is a non-PKM header within a PKM section - continue current section
                current_content.append(line)
            else:
                # This is a non-PKM header before any PKM section - part of preamble
                if not sections["_preamble"]:
                    sections["_preamble"] = "\n".join(lines[: i + 1])
                else:
                    sections["_preamble"] += "\n" + line
        elif current_section:
            # We're inside a PKM section
            current_content.append(line)
            last_pkm_section_end = i
        elif not any(sections.get(k) for k in sections if k.startswith("_") is False):
            # We haven't encountered any PKM sections yet - this is preamble
            if sections["_preamble"]:
                sections["_preamble"] += "\n" + line
            else:
                sections["_preamble"] = line

    # Save the last PKM section if any
    if current_section and current_content:
        sections[current_section] = "\n".join(current_content)

    # Everything after the last PKM section is postamble
    if last_pkm_section_end < len(lines) - 1:
        sections["_postamble"] = "\n".join(lines[last_pkm_section_end + 1 :])

    return sections


def _format_section(data: AggregatedData, section_name: str) -> str:
    """
    Format a single section from AggregatedData.

    Args:
        data: Aggregated data
        section_name: Section identifier (e.g., "calendar_events")

    Returns:
        Formatted markdown section
    """
    lines = []

    if section_name == "calendar_events" and data.calendar_events:
        lines.append("## 📅 Calendar Events")
        lines.append("")
        for event in sorted(data.calendar_events, key=lambda e: e.start):
            time_str = f"{event.start.strftime('%H:%M')} - {event.end.strftime('%H:%M')}"
            lines.append(f"- **{time_str}** {event.title}")
            if event.location:
                lines.append(f"  - Location: {event.location}")
            if event.description:
                lines.append(f"  - {event.description}")
        lines.append("")

    elif section_name == "github_activities" and data.github_activities:
        lines.append("## 🐙 GitHub Activities")
        lines.append("")
        for activity in sorted(data.github_activities, key=lambda a: a.timestamp):
            time_str = activity.timestamp.strftime("%H:%M")
            icon = {"commit": "📝", "pr": "🔀", "issue": "📋", "review": "👁️"}.get(
                activity.type, "•"
            )
            link_text = f"[{activity.repository}]({activity.url})"
            lines.append(f"- {icon} **{time_str}** {link_text} - {activity.title}")
            if activity.details:
                lines.append(f"  - {activity.details}")
        lines.append("")

    elif section_name == "atlassian_items" and data.atlassian_items:
        lines.append("## 🏢 Atlassian (Jira/Confluence)")
        lines.append("")
        for item in sorted(data.atlassian_items, key=lambda i: i.updated):
            icon = "📋" if item.type == "jira_issue" else "📄"
            status_str = f" ({item.status})" if item.status else ""
            lines.append(f"- {icon} [{item.key}]({item.url}) - {item.title}{status_str}")
        lines.append("")

    elif section_name == "things_tasks" and data.things_tasks:
        lines.append("## ✅ Things - Completed Tasks")
        lines.append("")
        for task in sorted(data.things_tasks, key=lambda t: t.completed_date):
            time_str = task.completed_date.strftime("%H:%M")
            project_str = f" ({task.project})" if task.project else ""
            tags_str = f" #{', #'.join(task.tags)}" if task.tags else ""
            lines.append(f"- **{time_str}** {task.title}{project_str}{tags_str}")
        lines.append("")

    elif section_name == "wakatime_activities" and data.wakatime_activities:
        lines.append("## ⏱️ Wakatime - Coding Activity")
        lines.append("")
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
        lines.append("")

    elif section_name == "google_docs" and data.google_docs:
        lines.append("## 📝 Google Docs")
        lines.append("")
        for doc in sorted(data.google_docs, key=lambda d: d.opened_at):
            time_str = doc.opened_at.strftime("%H:%M")
            lines.append(f"- **{time_str}** [{doc.title}]({doc.url})")
        lines.append("")

    elif section_name == "whoop_data" and (
        data.whoop_recovery or data.whoop_sleep or data.whoop_workouts
    ):
        lines.append("## 💪 Whoop Health Data")
        lines.append("")

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
                    f", Avg HR: {workout.average_heart_rate} bpm"
                    if workout.average_heart_rate
                    else ""
                )

                lines.append(
                    f"- **{time_str}** {workout.sport_name} ({duration_str}) - {strain_str}{hr_str}"
                )
            lines.append("")

    elif section_name == "errors":
        errors = {k: v for k, v in data.metadata.items() if k.endswith("_error")}
        if errors:
            lines.append("## ⚠️ Errors")
            lines.append("")
            for source, error in errors.items():
                source_name = source.replace("_error", "").replace("_", " ").title()
                lines.append(f"- **{source_name}:** {error}")
            lines.append("")

    return "\n".join(lines).rstrip()


def merge_sections(existing: dict[str, str], new_data: AggregatedData, format: str) -> str:
    """
    Merge existing file sections with new PKM data.

    - Preserve preamble and postamble (manual content)
    - Replace existing PKM sections with fresh data
    - Append new PKM sections that weren't in file

    Args:
        existing: Parsed sections from existing file
        new_data: New aggregated data
        format: Output format (should be "markdown")

    Returns:
        Merged markdown content
    """
    lines = []

    # Start with preamble (manual content before PKM sections)
    if existing.get("_preamble"):
        preamble = existing["_preamble"].rstrip()
        if preamble:
            lines.append(preamble)
            lines.append("")

    # Define section order for PKM sections
    section_order = [
        "calendar_events",
        "github_activities",
        "atlassian_items",
        "things_tasks",
        "wakatime_activities",
        "google_docs",
        "whoop_data",
        "errors",
    ]

    # Track which sections have been added
    added_sections = set()

    # First, add sections that existed in the original file (to maintain order)
    for section_name in section_order:
        if section_name in existing and section_name not in ["_preamble", "_postamble"]:
            # Replace with fresh data
            section_content = _format_section(new_data, section_name)
            if section_content:
                lines.append(section_content)
                added_sections.add(section_name)

    # Then add new sections that weren't in the original file
    for section_name in section_order:
        if section_name not in added_sections:
            section_content = _format_section(new_data, section_name)
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
    data: AggregatedData, output_path: Path, format: str, merge_existing: bool = True
) -> None:
    """
    Write report to file, optionally merging with existing content.

    Args:
        data: Data to write
        output_path: Target file path
        format: "markdown" or "json"
        merge_existing: If True and file exists, merge sections
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
        output = merge_sections(existing, data, format)
    else:
        output = format_as_markdown(data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output)
