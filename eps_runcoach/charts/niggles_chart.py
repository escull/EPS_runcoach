"""Chart of niggle severity over time, one line per body location."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime

from matplotlib.figure import Figure


def niggle_severity_chart(rows: list[sqlite3.Row]) -> Figure:
    figure = Figure(figsize=(6, 3.5), dpi=100)
    axes = figure.add_subplot(111)

    by_location: dict[str, list[tuple[datetime, int]]] = defaultdict(list)
    for row in rows:
        start_time = row["session_start_time"]
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        by_location[row["location"]].append((start_time, row["severity"]))

    for location, points in by_location.items():
        points.sort(key=lambda point: point[0])
        dates = [point[0] for point in points]
        severities = [point[1] for point in points]
        axes.plot(dates, severities, marker="o", label=location)

    axes.set_xlabel("Date")
    axes.set_ylabel("Severity (0-10)")
    axes.set_title("Niggle severity over time")
    axes.set_ylim(0, 10)
    if by_location:
        axes.legend(loc="upper left", fontsize="small")
    figure.autofmt_xdate()
    figure.tight_layout()
    return figure
