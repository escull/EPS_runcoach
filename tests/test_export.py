import csv
from datetime import datetime, timezone

from eps_runcoach.core import db
from eps_runcoach.core.export import TABLES, export_all_to_csv
from eps_runcoach.core.fit_import import SessionSummary


def make_summary(**overrides) -> SessionSummary:
    defaults = dict(
        sport="running",
        sub_sport="treadmill",
        start_time=datetime(2026, 9, 5, tzinfo=timezone.utc),
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


def test_export_writes_one_csv_per_table(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    output_dir = tmp_path / "export"

    written = export_all_to_csv(conn, output_dir)

    assert len(written) == len(TABLES)
    for table in TABLES:
        assert (output_dir / f"{table}.csv").exists()


def test_export_includes_real_session_data(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    session_id = db.insert_session(conn, make_summary(), file_hash="a", session_type="run")
    db.upsert_note(conn, session_id, rpe=7, note_text="Felt good", focus_tag=None)
    db.insert_niggle(conn, session_id, location="ankle", side="left", severity=3)

    output_dir = tmp_path / "export"
    export_all_to_csv(conn, output_dir)

    with (output_dir / "sessions.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["source_file"] == "test.fit"
    assert rows[0]["session_type"] == "run"

    with (output_dir / "notes.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["note_text"] == "Felt good"

    with (output_dir / "niggles.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["location"] == "ankle"


def test_export_handles_empty_tables_with_header_only(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    output_dir = tmp_path / "export"

    export_all_to_csv(conn, output_dir)

    with (output_dir / "sessions.csv").open(encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 1  # header only
    assert "source_file" in rows[0]
