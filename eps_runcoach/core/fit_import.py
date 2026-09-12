"""FIT file parsing: extracts a session summary and never retains GPS data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import fitdecode

# Any FIT field name containing these substrings carries GPS/location data and
# must never be read into memory or stored, per the project's privacy rule.
GPS_FIELD_MARKERS = ("position_lat", "position_long", "gps_accuracy")


@dataclass
class SessionSummary:
    sport: str
    sub_sport: str
    start_time: datetime | None
    total_distance_km: float | None
    total_duration_s: float | None
    avg_heart_rate: int | None
    max_heart_rate: int | None
    avg_pace_min_per_km: float | None
    calories: int | None
    total_ascent: float | None
    total_descent: float | None
    avg_cadence: float | None
    source_file: str


def _is_gps_field(field_name: str) -> bool:
    return any(marker in field_name for marker in GPS_FIELD_MARKERS)


def read_fit_session(path: str | Path) -> SessionSummary:
    """Parse a single FIT file into a session summary.

    Reads only the FIT `session` message (one per recorded activity), which
    already holds the totals and averages we need — there's no need to touch
    the per-second `record` stream (where any GPS points would live) for a
    summary. GPS-named fields are skipped defensively even so, in case a
    device ever puts them somewhere unexpected.
    """
    path = Path(path)
    session_data: dict[str, object] = {}

    with fitdecode.FitReader(str(path)) as fit:
        for frame in fit:
            if frame.frame_type != fitdecode.FIT_FRAME_DATA:
                continue
            if frame.name != "session":
                continue
            for field in frame.fields:
                if _is_gps_field(field.name):
                    continue
                session_data[field.name] = field.value
            break  # one activity per file — first session message is enough

    if not session_data:
        raise ValueError(f"No session data found in {path.name}")

    distance_m = session_data.get("total_distance")
    duration_s = session_data.get("total_timer_time")
    avg_speed = session_data.get("enhanced_avg_speed") or session_data.get("avg_speed")

    avg_pace_min_per_km = None
    if avg_speed:
        avg_pace_min_per_km = (1000 / avg_speed) / 60

    return SessionSummary(
        sport=str(session_data.get("sport", "unknown")),
        sub_sport=str(session_data.get("sub_sport", "unknown")),
        start_time=session_data.get("start_time"),
        total_distance_km=(distance_m / 1000) if distance_m else None,
        total_duration_s=duration_s,
        avg_heart_rate=session_data.get("avg_heart_rate"),
        max_heart_rate=session_data.get("max_heart_rate"),
        avg_pace_min_per_km=avg_pace_min_per_km,
        calories=session_data.get("total_calories"),
        total_ascent=session_data.get("total_ascent"),
        total_descent=session_data.get("total_descent"),
        avg_cadence=session_data.get("avg_running_cadence"),
        source_file=path.name,
    )
