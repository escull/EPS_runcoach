from datetime import date, datetime, timezone

from eps_runcoach.core import db, training_data
from eps_runcoach.core.fit_import import SessionSummary


def make_summary(**overrides) -> SessionSummary:
    defaults = dict(
        sport="running",
        sub_sport="treadmill",
        start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        total_distance_km=5.0,
        total_duration_s=1500.0,
        avg_heart_rate=140,
        max_heart_rate=160,
        avg_pace_min_per_km=5.0,
        calories=400,
        total_ascent=0.0,
        total_descent=0.0,
        avg_cadence=80.0,
        source_file="test.fit",
    )
    defaults.update(overrides)
    return SessionSummary(**defaults)


def test_build_snapshot_with_no_sessions(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    snapshot = training_data.build_snapshot(conn, resting_hr=60, max_hr=190)

    assert snapshot.dates == []
    assert snapshot.weekly_distance == {}
    assert snapshot.estimate_5k_seconds is None
    assert snapshot.latest_fitness is None


def test_build_snapshot_aggregates_run_session(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    session_id = db.insert_session(
        conn,
        make_summary(start_time=datetime(2026, 1, 5, tzinfo=timezone.utc)),  # a Monday
        file_hash="a",
        session_type="run",
    )
    db.upsert_note(conn, session_id, rpe=7, note_text="felt good", focus_tag=None)

    snapshot = training_data.build_snapshot(conn, resting_hr=60, max_hr=190, as_of=date(2026, 1, 10))

    assert snapshot.weekly_distance == {date(2026, 1, 5): 5.0}
    assert snapshot.latest_fitness is not None
    assert snapshot.latest_fitness > 0


def test_build_snapshot_separates_run_and_other_load(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    run_id = db.insert_session(
        conn, make_summary(start_time=datetime(2026, 1, 5, tzinfo=timezone.utc)), file_hash="run", session_type="run"
    )
    strength_id = db.insert_session(
        conn,
        make_summary(start_time=datetime(2026, 1, 5, tzinfo=timezone.utc), sport="training", sub_sport="unknown"),
        file_hash="strength",
        session_type="strength",
    )
    db.upsert_note(conn, strength_id, rpe=8, note_text=None, focus_tag="legs")

    snapshot = training_data.build_snapshot(conn, resting_hr=60, max_hr=190)

    week = date(2026, 1, 5)
    assert week in snapshot.weekly_run_load
    assert week in snapshot.weekly_other_load
    assert week not in snapshot.weekly_distance or snapshot.weekly_distance[week] == 5.0
