"""Chart-building functions for a single session's samples. Each returns a
matplotlib Figure (never pyplot) for the caller to embed with
FigureCanvasTkAgg.
"""

from __future__ import annotations

import sqlite3

from matplotlib.figure import Figure


def pace_chart(samples: list[sqlite3.Row]) -> Figure:
    figure = Figure(figsize=(6, 3), dpi=100)
    axes = figure.add_subplot(111)

    minutes = [s["elapsed_s"] / 60 for s in samples if s["speed_m_s"]]
    paces = [(1000 / s["speed_m_s"]) / 60 for s in samples if s["speed_m_s"]]

    axes.plot(minutes, paces, color="tab:blue")
    axes.set_xlabel("Elapsed time (min)")
    axes.set_ylabel("Pace (min/km)")
    axes.set_title("Pace")
    if paces:
        # pace charts read better with faster (lower) paces near the top
        axes.invert_yaxis()
    figure.tight_layout()
    return figure


def heart_rate_chart(samples: list[sqlite3.Row]) -> Figure:
    figure = Figure(figsize=(6, 3), dpi=100)
    axes = figure.add_subplot(111)

    minutes = [s["elapsed_s"] / 60 for s in samples if s["heart_rate"]]
    heart_rates = [s["heart_rate"] for s in samples if s["heart_rate"]]

    axes.plot(minutes, heart_rates, color="tab:red")
    axes.set_xlabel("Elapsed time (min)")
    axes.set_ylabel("Heart rate (bpm)")
    axes.set_title("Heart rate")
    figure.tight_layout()
    return figure
