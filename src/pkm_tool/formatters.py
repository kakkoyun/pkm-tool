"""Output formatters for PKM tool."""

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
                    f" - {sleep.sleep_efficiency:.0f}% efficiency"
                    if sleep.sleep_efficiency
                    else ""
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
