"""Aggregates raw sessions/notes/samples into the computed training
metrics used by both the Dashboard and the AI coach's context builder,
so the two don't duplicate this logic.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from eps_runcoach.core import db, metrics


def parse_session_date(start_time: str) -> date:
    return datetime.fromisoformat(start_time).date()


@dataclass
class TrainingSnapshot:
    dates: list[date] = field(default_factory=list)
    fitness: list[float] = field(default_factory=list)
    fatigue: list[float] = field(default_factory=list)
    form: list[float] = field(default_factory=list)
    weekly_distance: dict[date, float] = field(default_factory=dict)
    weekly_run_load: dict[date, float] = field(default_factory=dict)
    weekly_other_load: dict[date, float] = field(default_factory=dict)
    aerobic_points: list[tuple[date, float]] = field(default_factory=list)
    estimate_5k_seconds: float | None = None

    @property
    def latest_fitness(self) -> float | None:
        return self.fitness[-1] if len(self.fitness) else None

    @property
    def latest_fatigue(self) -> float | None:
        return self.fatigue[-1] if len(self.fatigue) else None

    @property
    def latest_form(self) -> float | None:
        return self.form[-1] if len(self.form) else None


def build_snapshot(
    conn: sqlite3.Connection, resting_hr: float, max_hr: float, as_of: date | None = None
) -> TrainingSnapshot:
    as_of = as_of or date.today()
    sessions = db.get_all_sessions(conn)

    session_loads: list[tuple[date, float]] = []
    run_sessions_for_estimate: list[tuple[date, float, float]] = []
    weekly_distance: dict[date, float] = {}
    weekly_run_load: dict[date, float] = {}
    weekly_other_load: dict[date, float] = {}
    aerobic_points: list[tuple[date, float]] = []

    for session in sessions:
        session_date = parse_session_date(session["start_time"])
        note = db.get_note(conn, session["id"])
        rpe = note["rpe"] if note else None

        trimp_value = metrics.trimp(session["avg_heart_rate"], session["duration_s"], resting_hr, max_hr)
        srpe_value = metrics.srpe_load(rpe, session["duration_s"])
        load = metrics.combined_session_load(trimp_value, srpe_value)
        if load is not None:
            session_loads.append((session_date, load))

        week_start = session_date - timedelta(days=session_date.weekday())
        if session["session_type"] == "run":
            weekly_distance[week_start] = weekly_distance.get(week_start, 0.0) + (session["distance_km"] or 0.0)
            if load is not None:
                weekly_run_load[week_start] = weekly_run_load.get(week_start, 0.0) + load
        elif load is not None:
            weekly_other_load[week_start] = weekly_other_load.get(week_start, 0.0) + load

        if session["session_type"] == "run" and session["distance_km"] and session["duration_s"]:
            run_sessions_for_estimate.append((session_date, session["distance_km"], session["duration_s"]))

            samples = db.get_samples(conn, session["id"])
            heart_rates = [sample["heart_rate"] for sample in samples]
            speeds = [sample["speed_m_s"] for sample in samples]
            pace = metrics.aerobic_efficiency_pace(heart_rates, speeds, resting_hr, max_hr)
            if pace is not None:
                aerobic_points.append((session_date, pace))

    dates, fitness, fatigue, form = metrics.fitness_fatigue_form(session_loads)
    aerobic_points.sort(key=lambda point: point[0])
    estimate_5k_seconds = metrics.estimate_5k_seconds(run_sessions_for_estimate, as_of=as_of)

    return TrainingSnapshot(
        dates=dates,
        fitness=list(fitness),
        fatigue=list(fatigue),
        form=list(form),
        weekly_distance=weekly_distance,
        weekly_run_load=weekly_run_load,
        weekly_other_load=weekly_other_load,
        aerobic_points=aerobic_points,
        estimate_5k_seconds=estimate_5k_seconds,
    )
