from pathlib import Path

from matplotlib.figure import Figure

from eps_runcoach.charts.session_charts import heart_rate_chart, pace_chart
from eps_runcoach.core import db
from eps_runcoach.core.fit_import import classify_session_type, parse_fit_file

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
