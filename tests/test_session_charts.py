from datetime import datetime, timezone
from pathlib import Path

from matplotlib.figure import Figure

from eps_runcoach.charts.session_charts import heart_rate_chart, pace_chart
from eps_runcoach.core import db
from eps_runcoach.core.fit_import import Sample, SessionSummary, classify_session_type, parse_fit_file

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"
TREADMILL_FIT = SAMPLE_DIR / "Treadmill_2026-09-08T18_29_35.fit"


def _stored_samples(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    parsed = parse_fit_file(TREADMILL_FIT)
    session_type = classify_session_type(parsed.summary.sport, parsed.summary.sub_sport)
    session_id = db.insert_session(conn, parsed.summary, file_hash="x", session_type=session_type)
    db.insert_samples(conn, session_id, parsed.samples)
    return db.get_samples(conn, session_id)


def test_pace_chart_returns_figure_with_data(tmp_path):
    samples = _stored_samples(tmp_path)

    figure = pace_chart(samples)

    assert isinstance(figure, Figure)
    line = figure.axes[0].lines[0]
    assert len(line.get_xdata()) > 0


def test_heart_rate_chart_returns_figure_with_data(tmp_path):
    samples = _stored_samples(tmp_path)

    figure = heart_rate_chart(samples)

    assert isinstance(figure, Figure)
    line = figure.axes[0].lines[0]
    assert len(line.get_xdata()) > 0


def test_charts_handle_no_samples_without_crashing():
    assert isinstance(pace_chart([]), Figure)
    assert isinstance(heart_rate_chart([]), Figure)


def test_pace_chart_excludes_near_stationary_outliers(tmp_path):
    # A near-zero speed sample (e.g. standing still before a treadmill
    # ramps up) implies an absurd pace that would otherwise dominate the
    # chart's y-axis and squash the real data into an unreadable sliver.
    conn = db.get_connection(tmp_path / "test.db")
    summary = SessionSummary(
        sport="running",
        sub_sport="treadmill",
        start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        total_distance_km=1.0,
        total_duration_s=300.0,
        avg_heart_rate=140,
        max_heart_rate=150,
        avg_pace_min_per_km=5.5,
        calories=100,
        total_ascent=0.0,
        total_descent=0.0,
        avg_cadence=80.0,
        source_file="test.fit",
    )
    session_id = db.insert_session(conn, summary, file_hash="x", session_type="run")
    samples = [
        Sample(elapsed_s=0.0, distance_km=0.0, speed_m_s=0.02, heart_rate=100, cadence=0, altitude_m=0),  # standing
        Sample(elapsed_s=5.0, distance_km=0.01, speed_m_s=3.0, heart_rate=130, cadence=80, altitude_m=0),
        Sample(elapsed_s=10.0, distance_km=0.02, speed_m_s=3.1, heart_rate=135, cadence=80, altitude_m=0),
    ]
    db.insert_samples(conn, session_id, samples)
    stored = db.get_samples(conn, session_id)

    figure = pace_chart(stored)

    paces = figure.axes[0].lines[0].get_ydata()
    assert len(paces) == 2  # the near-stationary sample is excluded
    assert max(paces) < 15  # nothing near the ~830 min/km the outlier would imply
