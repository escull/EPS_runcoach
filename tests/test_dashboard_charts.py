from datetime import date

from matplotlib.figure import Figure

from eps_runcoach.charts.dashboard_charts import (
    aerobic_efficiency_chart,
    fitness_fatigue_form_chart,
    weekly_distance_chart,
    weekly_load_chart,
)

DATES = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]


def test_fitness_fatigue_form_chart_has_three_lines():
    figure = fitness_fatigue_form_chart(DATES, [1, 2, 3], [1, 1, 1], [0, 1, 2])
    assert isinstance(figure, Figure)
    assert len(figure.axes[0].lines) == 3


def test_fitness_fatigue_form_chart_handles_empty_data():
    figure = fitness_fatigue_form_chart([], [], [], [])
    assert isinstance(figure, Figure)


def test_weekly_distance_chart_has_bars():
    figure = weekly_distance_chart(DATES, [10.0, 5.0, 8.0])
    assert isinstance(figure, Figure)
    assert len(figure.axes[0].patches) == 3


def test_weekly_load_chart_has_stacked_bars():
    figure = weekly_load_chart(DATES, [50, 40, 60], [10, 0, 20])
    assert isinstance(figure, Figure)
    assert len(figure.axes[0].patches) == 6  # 3 weeks x 2 stacked series


def test_aerobic_efficiency_chart_has_line():
    figure = aerobic_efficiency_chart(DATES, [5.5, 5.4, 5.3])
    assert isinstance(figure, Figure)
    assert len(figure.axes[0].lines) == 1


def test_aerobic_efficiency_chart_handles_empty_data():
    figure = aerobic_efficiency_chart([], [])
    assert isinstance(figure, Figure)
