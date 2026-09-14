from matplotlib.figure import Figure

from eps_runcoach.charts.body_chart import weight_chart
from eps_runcoach.core import db


def test_weight_chart_with_data(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    db.insert_body_metric(conn, "2026-06-01", weight_kg=76.0)
    db.insert_body_metric(conn, "2026-06-15", weight_kg=75.0)
    rows = db.get_all_body_metrics(conn)

    figure = weight_chart(rows)

    assert isinstance(figure, Figure)
    line = figure.axes[0].lines[0]
    assert list(line.get_ydata()) == [76.0, 75.0]


def test_weight_chart_handles_no_data():
    figure = weight_chart([])
    assert isinstance(figure, Figure)
    assert len(figure.axes[0].lines) == 0
