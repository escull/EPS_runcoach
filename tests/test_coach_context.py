from datetime import date, datetime, timezone

from eps_runcoach.core import db, settings
from eps_runcoach.core.coach.context import build_context
from eps_runcoach.core.fit_import import SessionSummary


def make_summary(**overrides) -> SessionSummary:
    defaults = dict(
        sport="running",
        sub_sport="treadmill",
        start_time=datetime(2026, 9, 5, tzinfo=timezone.utc),
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


def test_build_context_without_hr_settings(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    context = build_context(conn, as_of=date(2026, 9, 10))

    assert "Max heart rate: not set" in context
    assert "unavailable" in context


def test_build_context_includes_goal_and_recent_session_detail(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    settings.set_setting(conn, settings.MAX_HEART_RATE_KEY, "190")
    settings.set_setting(conn, settings.RESTING_HEART_RATE_KEY, "60")
    settings.set_setting(conn, settings.GOAL_5K_SECONDS_KEY, "1500")

    session_id = db.insert_session(conn, make_summary(), file_hash="a", session_type="run")
    db.upsert_note(conn, session_id, rpe=7, note_text="Felt strong today", focus_tag=None)
    db.insert_niggle(conn, session_id, location="ankle", side="left", severity=4)

    context = build_context(conn, as_of=date(2026, 9, 10))

    assert "5k goal: 25:00" in context
    assert "RPE 7/10" in context
    assert '"Felt strong today"' in context
    assert "ankle (left) 4/10" in context
    assert "Fitness:" in context


def test_build_context_excludes_sessions_outside_the_recent_window(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    settings.set_setting(conn, settings.MAX_HEART_RATE_KEY, "190")
    settings.set_setting(conn, settings.RESTING_HEART_RATE_KEY, "60")

    db.insert_session(
        conn,
        make_summary(start_time=datetime(2026, 8, 1, tzinfo=timezone.utc), source_file="old.fit"),
        file_hash="old",
        session_type="run",
    )

    context = build_context(conn, as_of=date(2026, 9, 10))

    assert "(no sessions in this window)" in context


def test_build_context_never_contains_gps_or_filename():
    # Static invariant check: nothing in fit_import/db exposes raw filenames
    # or GPS to the text summary - describe_session only pulls from
    # summarised session/note/niggle fields.
    import inspect

    from eps_runcoach.core.coach import context as context_module

    source = inspect.getsource(context_module)
    assert "source_file" not in source
    assert "position_lat" not in source
    assert "position_long" not in source
