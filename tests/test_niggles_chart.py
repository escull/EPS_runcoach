from datetime import datetime, timezone

from matplotlib.figure import Figure

from eps_runcoach.charts.niggles_chart import niggle_severity_chart
from eps_runcoach.core import db
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


def test_niggle_severity_chart_with_data(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    session_id = db.insert_session(conn, make_summary(), file_hash="one", session_type="run")
    db.insert_niggle(conn, session_id, location="ankle", side="left", severity=4)
    db.insert_niggle(conn, session_id, location="knee", side=None, severity=2)
    rows = db.get_all_niggles_with_dates(conn)

    figure = niggle_severity_chart(rows)

    assert isinstance(figure, Figure)
    axes = figure.axes[0]
    assert len(axes.lines) == 2  # one line per location


def test_niggle_severity_chart_handles_no_data():
    figure = niggle_severity_chart([])
    assert isinstance(figure, Figure)
    assert len(figure.axes[0].lines) == 0
