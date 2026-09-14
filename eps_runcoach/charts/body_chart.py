"""Chart of body weight over time."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from matplotlib.figure import Figure


def weight_chart(rows: list[sqlite3.Row]) -> Figure:
    figure = Figure(figsize=(6, 3.5), dpi=100)
    axes = figure.add_subplot(111)

    entries = [row for row in rows if row["weight_kg"] is not None]
    if entries:
        dates = [datetime.fromisoformat(row["recorded_date"]) for row in entries]
        weights = [row["weight_kg"] for row in entries]
        axes.plot(dates, weights, marker="o", color="tab:green")
    axes.set_xlabel("Date")
    axes.set_ylabel("Weight (kg)")
    axes.set_title("Weight over time")
    figure.autofmt_xdate()
    figure.tight_layout()
    return figure
