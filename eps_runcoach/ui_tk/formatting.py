"""Presentation-only formatting helpers, used by pages to display session
data in kilometres, min/km pace and UK date order.
"""

from __future__ import annotations

from datetime import datetime


def format_date(value: str | datetime | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime("%d/%m/%Y")


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_distance(km: float | None) -> str:
    if km is None:
        return "-"
    return f"{km:.2f} km"


def format_pace(min_per_km: float | None) -> str:
    if not min_per_km:
        return "-"
    minutes = int(min_per_km)
    seconds = round((min_per_km - minutes) * 60)
    if seconds == 60:
        minutes += 1
        seconds = 0
    return f"{minutes}:{seconds:02d} /km"


def format_hr(bpm: int | None) -> str:
    if bpm is None:
        return "-"
    return f"{bpm} bpm"
