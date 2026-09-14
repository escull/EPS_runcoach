"""Builds the compact text summary sent to the AI coach: goal/settings,
recent weekly totals, session-by-session detail for the last 10 days,
current fitness/fatigue/form, and the latest 5k estimate. Never includes
GPS, names, or raw files - only summarised stats and notes (nothing
tracked in this app includes any of those anyway).
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from eps_runcoach.core import db, training_data
from eps_runcoach.core import settings as core_settings
from eps_runcoach.core.formatting import (
    format_date,
    format_distance,
    format_duration,
    format_hr,
    format_pace,
    format_recovery_time,
    format_training_effect,
)

RECENT_SESSION_DAYS = 10
WEEKLY_TOTALS_WEEKS = 4


def build_context(conn: sqlite3.Connection, as_of: date | None = None, since: date | None = None) -> str:
    """Build the text summary. By default, the session-detail section
    covers the last RECENT_SESSION_DAYS days; pass `since` to cover a
    specific window instead (e.g. everything since the coach was last
    consulted, for the AI Insights page's holistic "catch-up" review).
    """
    as_of = as_of or date.today()

    max_hr_raw = core_settings.get_setting(conn, core_settings.MAX_HEART_RATE_KEY)
    resting_hr_raw = core_settings.get_setting(conn, core_settings.RESTING_HEART_RATE_KEY)
    goal_raw = core_settings.get_setting(conn, core_settings.GOAL_5K_SECONDS_KEY)
    goal_seconds = float(goal_raw) if goal_raw else core_settings.DEFAULT_GOAL_5K_SECONDS

    snapshot = None
    if max_hr_raw and resting_hr_raw:
        snapshot = training_data.build_snapshot(conn, float(resting_hr_raw), float(max_hr_raw), as_of=as_of)

    session_window_start = since if since is not None else as_of - timedelta(days=RECENT_SESSION_DAYS)
    window_label = f"since {format_date(session_window_start.isoformat())}" if since is not None else "from the last 10 days"

    height_raw = core_settings.get_setting(conn, core_settings.HEIGHT_CM_KEY)

    lines: list[str] = []
    lines.append("=== Goal and settings ===")
    lines.append(f"5k goal: {format_duration(goal_seconds)}")
    lines.append(f"Max heart rate: {max_hr_raw} bpm" if max_hr_raw else "Max heart rate: not set")
    lines.append(f"Resting heart rate: {resting_hr_raw} bpm" if resting_hr_raw else "Resting heart rate: not set")
    if height_raw:
        lines.append(f"Height: {height_raw} cm")

    lines.append("")
    lines.append("=== Body ===")
    lines.extend(_weight_trend_lines(conn, as_of))

    lines.append("")
    lines.append(f"=== Weekly totals (last {WEEKLY_TOTALS_WEEKS} weeks) ===")
    lines.extend(_weekly_totals_lines(snapshot, as_of))

    lines.append("")
    lines.append(f"=== Sessions {window_label} ===")
    lines.extend(_recent_session_lines(conn, session_window_start))

    lines.append("")
    lines.append("=== Current training state ===")
    lines.extend(_training_state_lines(snapshot))

    return "\n".join(lines)


def _weight_trend_lines(conn: sqlite3.Connection, as_of: date) -> list[str]:
    weighed_rows = [row for row in db.get_all_body_metrics(conn) if row["weight_kg"] is not None]
    if not weighed_rows:
        return ["(no weight logged yet)"]

    latest = weighed_rows[-1]
    lines = [f"Weight: {latest['weight_kg']:.1f} kg (as of {format_date(latest['recorded_date'])})"]

    window_start = as_of - timedelta(weeks=WEEKLY_TOTALS_WEEKS)
    earlier_in_window = [row for row in weighed_rows if date.fromisoformat(row["recorded_date"]) <= window_start]
    if earlier_in_window:
        change = latest["weight_kg"] - earlier_in_window[-1]["weight_kg"]
        if abs(change) < 0.05:
            lines.append(f"No real change over the last {WEEKLY_TOTALS_WEEKS} weeks")
        else:
            direction = "up" if change > 0 else "down"
            lines.append(f"{direction.capitalize()} {abs(change):.1f} kg over the last {WEEKLY_TOTALS_WEEKS} weeks")

    return lines


def _weekly_totals_lines(snapshot: training_data.TrainingSnapshot | None, as_of: date) -> list[str]:
    if snapshot is None:
        return ["(unavailable - heart rate settings not configured)"]

    current_week_start = as_of - timedelta(days=as_of.weekday())
    week_starts = [current_week_start - timedelta(weeks=i) for i in range(WEEKLY_TOTALS_WEEKS)]
    week_starts.reverse()

    lines = []
    for week_start in week_starts:
        distance = snapshot.weekly_distance.get(week_start, 0.0)
        run_load = snapshot.weekly_run_load.get(week_start, 0.0)
        other_load = snapshot.weekly_other_load.get(week_start, 0.0)
        lines.append(
            f"Week of {format_date(week_start.isoformat())}: "
            f"{distance:.1f} km running, run load {run_load:.0f}, other load {other_load:.0f}"
        )
    return lines


def _recent_session_lines(conn: sqlite3.Connection, cutoff: date) -> list[str]:
    sessions = db.get_all_sessions(conn)
    recent = [s for s in sessions if training_data.parse_session_date(s["start_time"]) >= cutoff]

    if not recent:
        return ["(no sessions in this window)"]

    return [_describe_session(conn, session) for session in reversed(recent)]  # oldest first


def _training_state_lines(snapshot: training_data.TrainingSnapshot | None) -> list[str]:
    if snapshot is None or snapshot.latest_fitness is None:
        lines = ["(unavailable - heart rate settings not configured, or no sessions yet)"]
    else:
        lines = [
            f"Fitness: {snapshot.latest_fitness:.0f}",
            f"Fatigue: {snapshot.latest_fatigue:.0f}",
            f"Form: {snapshot.latest_form:.0f}",
        ]

    if snapshot is not None and snapshot.estimate_5k_seconds is not None:
        lines.append(f"Latest 5k estimate: {format_duration(snapshot.estimate_5k_seconds)}")
    else:
        lines.append("Latest 5k estimate: not enough recent data")

    return lines


def _describe_session(conn: sqlite3.Connection, session: sqlite3.Row) -> str:
    parts = [
        f"- {format_date(session['start_time'])} {session['session_type']} "
        f"({session['sport']}/{session['sub_sport']}): duration {format_duration(session['duration_s'])}"
    ]
    if session["distance_km"]:
        parts.append(f"distance {format_distance(session['distance_km'])}")
        parts.append(f"pace {format_pace(session['avg_pace_min_per_km'])}")
    if session["avg_heart_rate"]:
        parts.append(f"avg HR {format_hr(session['avg_heart_rate'])}")
    if session["recovery_time_s"]:
        parts.append(f"recovery time {format_recovery_time(session['recovery_time_s'])}")
    if session["total_training_effect"] is not None:
        parts.append(f"training effect {format_training_effect(session['total_training_effect'])}")

    note = db.get_note(conn, session["id"])
    if note and note["rpe"] is not None:
        parts.append(f"RPE {note['rpe']}/10")
    if note and note["focus_tag"]:
        parts.append(f"focus {note['focus_tag']}")

    text = ", ".join(parts)

    if note and note["note_text"]:
        text += f'\n  note: "{note["note_text"]}"'

    niggles = db.get_niggles_for_session(conn, session["id"])
    if niggles:
        descriptions = []
        for niggle in niggles:
            side = niggle["side"]
            side_text = f" ({side})" if side else ""
            descriptions.append(f"{niggle['location']}{side_text} {niggle['severity']}/10")
        text += f"\n  niggles: {', '.join(descriptions)}"

    return text
