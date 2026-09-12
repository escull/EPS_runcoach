"""Chart-building functions for the Dashboard page. Each returns a
matplotlib Figure (never pyplot).
"""

from __future__ import annotations

from datetime import date

from matplotlib.figure import Figure


def fitness_fatigue_form_chart(dates: list[date], fitness, fatigue, form) -> Figure:
    figure = Figure(figsize=(6, 3), dpi=100)
    axes = figure.add_subplot(111)

    axes.plot(dates, fitness, label="Fitness", color="tab:blue")
    axes.plot(dates, fatigue, label="Fatigue", color="tab:orange")
    axes.plot(dates, form, label="Form", color="tab:green")

    axes.set_xlabel("Date")
    axes.set_ylabel("Load")
    axes.set_title("Fitness, fatigue and form")
    if dates:
        axes.legend(loc="upper left", fontsize="small")
    figure.autofmt_xdate()
    figure.tight_layout()
    return figure


def weekly_distance_chart(week_starts: list[date], distances_km: list[float]) -> Figure:
    figure = Figure(figsize=(6, 3), dpi=100)
    axes = figure.add_subplot(111)

    axes.bar(week_starts, distances_km, width=5.5, color="tab:blue")
    axes.set_xlabel("Week")
    axes.set_ylabel("Distance (km)")
    axes.set_title("Weekly running distance")
    figure.autofmt_xdate()
    figure.tight_layout()
    return figure


def weekly_load_chart(week_starts: list[date], run_loads: list[float], other_loads: list[float]) -> Figure:
    figure = Figure(figsize=(6, 3), dpi=100)
    axes = figure.add_subplot(111)

    axes.bar(week_starts, run_loads, width=5.5, color="tab:blue", label="Running")
    axes.bar(week_starts, other_loads, width=5.5, bottom=run_loads, color="tab:orange", label="Gym / other")

    axes.set_xlabel("Week")
    axes.set_ylabel("Training load")
    axes.set_title("Weekly training load")
    if week_starts:
        axes.legend(loc="upper left", fontsize="small")
    figure.autofmt_xdate()
    figure.tight_layout()
    return figure


def aerobic_efficiency_chart(dates: list[date], paces_min_per_km: list[float]) -> Figure:
    figure = Figure(figsize=(6, 3), dpi=100)
    axes = figure.add_subplot(111)

    axes.plot(dates, paces_min_per_km, marker="o", color="tab:purple")
    axes.set_xlabel("Date")
    axes.set_ylabel("Pace at easy HR (min/km)")
    axes.set_title("Aerobic efficiency")
    if paces_min_per_km:
        axes.invert_yaxis()  # faster pace (lower value) reads as "better", near the top
    figure.autofmt_xdate()
    figure.tight_layout()
    return figure
