"""Exports every user data table to its own CSV file - the Settings
page's "Export all data to CSV" option.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

TABLES = ["sessions", "splits", "samples", "notes", "niggles", "body_metrics", "settings", "ai_reviews"]


def export_all_to_csv(conn: sqlite3.Connection, output_dir: str | Path) -> list[Path]:
    """Write each table in TABLES to <output_dir>/<table>.csv. Returns the
    list of files written (tables with no rows still get a header-only
    file, so the export is predictable).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for table in TABLES:
        # table is always one of the fixed names above, never user input,
        # so interpolating it into SQL here is safe.
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        columns = [description[0] for description in conn.execute(f"SELECT * FROM {table} LIMIT 0").description]

        file_path = output_dir / f"{table}.csv"
        with file_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for row in rows:
                writer.writerow(tuple(row))
        written.append(file_path)

    return written
