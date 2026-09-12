"""FIT file parsing: extracts session, split and sample data, and never
retains GPS data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import fitdecode

# Any FIT field name containing these substrings carries GPS/location data and
# must never be read into memory or stored, per the project's privacy rule.
GPS_FIELD_MARKERS = ("position_lat", "position_long", "gps_accuracy")

# Time-series samples are downsampled to one row per this many seconds.
SAMPLE_INTERVAL_S = 5.0


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


@dataclass
class SplitSummary:
    split_index: int
    distance_km: float | None
    duration_s: float | None
    avg_pace_min_per_km: float | None
    avg_heart_rate: int | None


@dataclass
class Sample:
    elapsed_s: float
    distance_km: float | None
    speed_m_s: float | None
    heart_rate: int | None
    cadence: float | None
    altitude_m: float | None


@dataclass
class ParsedFitFile:
    summary: SessionSummary
    splits: list[SplitSummary] = field(default_factory=list)
    samples: list[Sample] = field(default_factory=list)


def _is_gps_field(field_name: str) -> bool:
    return any(marker in field_name for marker in GPS_FIELD_MARKERS)


def _frame_fields(frame) -> dict[str, object]:
    return {f.name: f.value for f in frame.fields if not _is_gps_field(f.name)}


def _pace_min_per_km(speed_m_s: float | None) -> float | None:
    if not speed_m_s:
        return None
    return (1000 / speed_m_s) / 60


def _build_summary(session_data: dict[str, object], path: Path) -> SessionSummary:
    distance_m = session_data.get("total_distance")
    avg_speed = session_data.get("enhanced_avg_speed") or session_data.get("avg_speed")

    return SessionSummary(
        sport=str(session_data.get("sport", "unknown")),
        sub_sport=str(session_data.get("sub_sport", "unknown")),
        start_time=session_data.get("start_time"),
        total_distance_km=(distance_m / 1000) if distance_m else None,
        total_duration_s=session_data.get("total_timer_time"),
        avg_heart_rate=session_data.get("avg_heart_rate"),
        max_heart_rate=session_data.get("max_heart_rate"),
        avg_pace_min_per_km=_pace_min_per_km(avg_speed),
        calories=session_data.get("total_calories"),
        total_ascent=session_data.get("total_ascent"),
        total_descent=session_data.get("total_descent"),
        avg_cadence=session_data.get("avg_running_cadence"),
        source_file=path.name,
    )


def _build_split(lap_data: dict[str, object], split_index: int) -> SplitSummary:
    distance_m = lap_data.get("total_distance")
    avg_speed = lap_data.get("enhanced_avg_speed") or lap_data.get("avg_speed")

    return SplitSummary(
        split_index=split_index,
        distance_km=(distance_m / 1000) if distance_m else None,
        duration_s=lap_data.get("total_timer_time"),
        avg_pace_min_per_km=_pace_min_per_km(avg_speed),
        avg_heart_rate=lap_data.get("avg_heart_rate"),
    )


def _build_sample(bucket_index: int, bucket_data: dict[str, object]) -> Sample:
    distance_m = bucket_data.get("distance")
    speed = bucket_data.get("enhanced_speed") or bucket_data.get("speed")
    altitude = bucket_data.get("enhanced_altitude") or bucket_data.get("altitude")

    return Sample(
        elapsed_s=bucket_index * SAMPLE_INTERVAL_S,
        distance_km=(distance_m / 1000) if distance_m is not None else None,
        speed_m_s=speed,
        heart_rate=bucket_data.get("heart_rate"),
        cadence=bucket_data.get("cadence"),
        altitude_m=altitude,
    )


def parse_fit_file(path: str | Path) -> ParsedFitFile:
    """Parse a single FIT file into a session summary, splits and samples.

    Two passes are made over the file: the first finds the `session`
    message and its start time; the second builds splits from `lap`
    messages and samples from `record` messages, using that start time to
    compute each sample's elapsed seconds. A second pass is needed because
    `session` is written near the end of the file, after the laps and
    records it summarises.

    Records are merged and downsampled to one row per SAMPLE_INTERVAL_S:
    devices often split one moment's reading across several `record`
    messages (e.g. heart rate separately from distance/speed), so readings
    falling in the same time bucket are merged rather than the first one
    simply winning.

    GPS-named fields (position_lat/position_long) are never read into
    memory, for any message type.
    """
    path = Path(path)

    session_data: dict[str, object] = {}
    with fitdecode.FitReader(str(path)) as fit:
        for frame in fit:
            if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "session":
                session_data = _frame_fields(frame)
                break

    if not session_data:
        raise ValueError(f"No session data found in {path.name}")

    start_time = session_data.get("start_time")
    splits: list[SplitSummary] = []
    samples: list[Sample] = []
    current_bucket: int | None = None
    bucket_data: dict[str, object] = {}

    def flush_bucket() -> None:
        if current_bucket is not None:
            samples.append(_build_sample(current_bucket, bucket_data))

    with fitdecode.FitReader(str(path)) as fit:
        for frame in fit:
            if frame.frame_type != fitdecode.FIT_FRAME_DATA:
                continue

            if frame.name == "lap":
                lap_data = _frame_fields(frame)
                splits.append(_build_split(lap_data, len(splits) + 1))

            elif frame.name == "record" and start_time is not None:
                record_data = _frame_fields(frame)
                timestamp = record_data.pop("timestamp", None)
                if timestamp is None:
                    continue

                elapsed_s = (timestamp - start_time).total_seconds()
                bucket = int(elapsed_s // SAMPLE_INTERVAL_S)
                if bucket != current_bucket:
                    flush_bucket()
                    bucket_data = {}
                    current_bucket = bucket
                bucket_data.update(record_data)

    flush_bucket()

    return ParsedFitFile(
        summary=_build_summary(session_data, path),
        splits=splits,
        samples=samples,
    )
