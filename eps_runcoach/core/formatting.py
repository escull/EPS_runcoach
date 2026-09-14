"""Presentation-only formatting helpers: kilometres, min/km pace, UK date
order. Lives in core (not ui_tk) because the coach's context builder needs
these too, and core can't depend on ui_tk.
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


def format_vo2_max(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.0f} ml/min/kg"


def format_recovery_time(seconds: float | None) -> str:
    if not seconds:
        return "-"
    hours = seconds / 3600
    if hours < 1:
        return f"{int(seconds / 60)} min"
    return f"{hours:.0f}h"


def format_training_effect(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.1f}/5.0"


def parse_ddmmyyyy_to_iso_date(text: str) -> str | None:
    """Parse a "DD/MM/YYYY" string (as typed for a logged date) into an ISO
    date string. None if the text isn't a valid date.
    """
    try:
        return datetime.strptime(text.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def parse_mmss_to_seconds(text: str) -> float | None:
    """Parse a "MM:SS" or "H:MM:SS" string (as typed for a goal time) into
    seconds. None if the text isn't a valid time.
    """
    parts = text.strip().split(":")
    if not 2 <= len(parts) <= 3 or not all(p.isdigit() for p in parts):
        return None
    parts_int = [int(p) for p in parts]
    if len(parts_int) == 2:
        minutes, seconds = parts_int
        hours = 0
    else:
        hours, minutes, seconds = parts_int
    if seconds >= 60 or minutes >= 60:
        return None
    return float(hours * 3600 + minutes * 60 + seconds)
