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


def test_build_context_includes_recovery_time_and_training_effect_when_present(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    settings.set_setting(conn, settings.MAX_HEART_RATE_KEY, "190")
    settings.set_setting(conn, settings.RESTING_HEART_RATE_KEY, "60")

    db.insert_session(
        conn,
        make_summary(recovery_time_s=28980.0, total_training_effect=3.0),
        file_hash="hrm",
        session_type="run",
    )

    context = build_context(conn, as_of=date(2026, 9, 10))

    assert "recovery time 8h" in context
    assert "training effect 3.0/5.0" in context


def test_build_context_reports_no_weight_logged_by_default(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")

    context = build_context(conn, as_of=date(2026, 9, 10))

    assert "(no weight logged yet)" in context


def test_build_context_includes_weight_trend_over_four_weeks(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    settings.set_setting(conn, settings.HEIGHT_CM_KEY, "180")
    db.insert_body_metric(conn, "2026-08-01", weight_kg=76.0)  # more than 4 weeks before as_of
    db.insert_body_metric(conn, "2026-09-08", weight_kg=74.9)

    context = build_context(conn, as_of=date(2026, 9, 10))

    assert "Height: 180 cm" in context
    assert "Weight: 74.9 kg" in context
    assert "Down 1.1 kg over the last 4 weeks" in context


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


def test_build_context_since_overrides_the_default_window():
    conn = db.get_connection(":memory:")
    db.insert_session(
        conn,
        make_summary(start_time=datetime(2026, 8, 1, tzinfo=timezone.utc), source_file="old.fit"),
        file_hash="old",
        session_type="run",
    )

    # Would be excluded by the default 10-day window, but "since" reaches back further
    context = build_context(conn, as_of=date(2026, 9, 10), since=date(2026, 7, 1))

    assert "since 01/07/2026" in context
    assert "(no sessions in this window)" not in context
    assert "01/08/2026" in context


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
