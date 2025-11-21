"""Output formatters for PKM tool."""

import json
from datetime import date

from pkm_tool.models import AggregatedData


def _humanize_source_key(metadata_key: str) -> str:
    """Convert metadata keys into human-friendly source names."""
    normalized = (
        metadata_key.replace("_error", "")
        .replace("_skipped", "")
        .replace("_", " ")
        .strip()
        .lower()
    )
    overrides = {
        "github": "GitHub",
        "google docs": "Google Docs",
        "apple calendar": "Apple Calendar",
        "wakatime": "Wakatime",
        "things": "Things",
        "atlassian": "Atlassian",
    }
    return overrides.get(normalized, normalized.title())


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

        if data.whoop_recovery:
            recovery = data.whoop_recovery
            lines.append(
                f"**Recovery:** {recovery.recovery_score:.0f}% "
                f"(HRV: {recovery.hrv:.0f}ms, Resting HR: {recovery.resting_heart_rate} bpm)"
            )
            if recovery.spo2 is not None or recovery.skin_temp is not None:
                extras = []
                if recovery.spo2 is not None:
                    extras.append(f"SpO₂: {recovery.spo2:.0f}%")
                if recovery.skin_temp is not None:
                    extras.append(f"Skin temp: {recovery.skin_temp:.1f}°C")
                lines.append(f"  - {', '.join(extras)}")
            lines.append("")

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

        if data.whoop_workouts:
            lines.append("**Workouts:**")
            for workout in sorted(data.whoop_workouts, key=lambda w: w.start):
                time_str = workout.start.strftime("%H:%M")
                hours = workout.duration_minutes // 60
                mins = workout.duration_minutes % 60
                duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
                strain_str = f"Strain: {workout.strain:.1f}"
                hr_bits = []
                if workout.average_heart_rate:
                    hr_bits.append(f"Avg HR: {workout.average_heart_rate} bpm")
                if workout.max_heart_rate:
                    hr_bits.append(f"Max HR: {workout.max_heart_rate} bpm")
                lines.append(
                    f"- **{time_str}** {workout.sport_name} ({duration_str}) - "
                    f"{strain_str}{', ' + ', '.join(hr_bits) if hr_bits else ''}"
                )
            lines.append("")

    # Errors
    errors = {k: v for k, v in data.metadata.items() if k.endswith("_error")}
    if errors:
        lines.append("## ⚠️ Errors")
        lines.append("")
        for source, error in errors.items():
            source_name = _humanize_source_key(source)
            lines.append(f"- **{source_name}:** {error}")
        lines.append("")

    skipped = {k: v for k, v in data.metadata.items() if k.endswith("_skipped")}
    if skipped:
        lines.append("## ⏭️ Skipped Sources")
        lines.append("")
        for source, reason in skipped.items():
            source_name = _humanize_source_key(source)
            lines.append(f"- **{source_name}:** {reason}")
        lines.append("")

    return "\n".join(lines)


def format_reports_as_markdown(
    reports: list[AggregatedData],
    date_range: tuple[date, date] | None,
) -> str:
    """
    Format multiple daily reports as Markdown with separators and summary.
    """
    if not reports:
        return "# Daily Report\n\n_No data for the requested dates._"
    if len(reports) == 1:
        return format_as_markdown(reports[0])

    start_date, end_date = date_range or (reports[0].date, reports[-1].date)
    summary_block = "\n".join(
        [
            "# Daily Reports Summary",
            "",
            f"- Start: {start_date}",
            f"- End: {end_date}",
            f"- Days: {len(reports)}",
            "",
        ]
    ).strip()
    report_blocks = "\n---\n".join(format_as_markdown(report).strip() for report in reports)
    return f"{summary_block}\n\n{report_blocks}".strip()


def format_reports_as_json(
    reports: list[AggregatedData],
    date_range: tuple[date, date] | None,
) -> str:
    """
    Format multiple daily reports as JSON. Includes a leading summary object
    followed by one entry per day.
    """
    if not reports:
        return json.dumps([], indent=2)
    if len(reports) == 1:
        return format_as_json(reports[0])

    start_date, end_date = date_range or (reports[0].date, reports[-1].date)
    payload: list[dict] = [
        {
            "summary": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": len(reports),
            }
        }
    ]
    payload.extend(report.model_dump(mode="json") for report in reports)
    return json.dumps(payload, indent=2)
