import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from eps_runcoach.core import db
from eps_runcoach.core.fit_import import Sample, SessionSummary, SplitSummary


def make_summary(**overrides) -> SessionSummary:
    defaults = dict(
        sport="running",
        sub_sport="treadmill",
        start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
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


@pytest.fixture
def conn(tmp_path) -> sqlite3.Connection:
    return db.get_connection(tmp_path / "test.db")


def test_init_db_creates_all_tables(conn):
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    expected = {
        "schema_version",
        "sessions",
        "splits",
        "samples",
        "notes",
        "niggles",
        "settings",
        "ai_reviews",
    }
    assert expected.issubset(tables)

    version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
    assert version == db.MIGRATIONS[-1][0]


def test_insert_and_fetch_session(conn):
    summary = make_summary()
    session_id = db.insert_session(conn, summary, file_hash="abc123", session_type="run")

    assert session_id is not None
    assert db.session_exists(conn, "abc123")
    assert not db.session_exists(conn, "does-not-exist")

    row = db.get_session_by_hash(conn, "abc123")
    assert row["source_file"] == "test.fit"
    assert row["session_type"] == "run"
    assert row["distance_km"] == 5.0


def test_duplicate_file_hash_rejected(conn):
    summary = make_summary()
    db.insert_session(conn, summary, file_hash="dup", session_type="run")

    with pytest.raises(sqlite3.IntegrityError):
        db.insert_session(conn, summary, file_hash="dup", session_type="run")


def test_insert_splits_and_samples(conn):
    summary = make_summary()
    session_id = db.insert_session(conn, summary, file_hash="withdata", session_type="run")

    splits = [
        SplitSummary(split_index=1, distance_km=1.0, duration_s=300.0, avg_pace_min_per_km=5.0, avg_heart_rate=140),
        SplitSummary(split_index=2, distance_km=1.0, duration_s=290.0, avg_pace_min_per_km=4.8, avg_heart_rate=145),
    ]
    samples = [
        Sample(elapsed_s=0.0, distance_km=0.0, speed_m_s=3.3, heart_rate=130, cadence=80.0, altitude_m=10.0),
        Sample(elapsed_s=5.0, distance_km=0.02, speed_m_s=3.3, heart_rate=132, cadence=80.0, altitude_m=10.0),
    ]

    db.insert_splits(conn, session_id, splits)
    db.insert_samples(conn, session_id, samples)

    stored_splits = conn.execute("SELECT * FROM splits WHERE session_id = ?", (session_id,)).fetchall()
    stored_samples = conn.execute("SELECT * FROM samples WHERE session_id = ?", (session_id,)).fetchall()

    assert len(stored_splits) == 2
    assert len(stored_samples) == 2
    assert stored_splits[0]["distance_km"] == 1.0
    assert stored_samples[1]["heart_rate"] == 132


def test_deleting_session_cascades_to_splits_and_samples(conn):
    summary = make_summary()
    session_id = db.insert_session(conn, summary, file_hash="cascade", session_type="run")
    db.insert_splits(conn, session_id, [SplitSummary(1, 1.0, 300.0, 5.0, 140)])
    db.insert_samples(conn, session_id, [Sample(0.0, 0.0, 3.3, 130, 80.0, 10.0)])

    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()

    assert conn.execute("SELECT COUNT(*) AS n FROM splits").fetchone()["n"] == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM samples").fetchone()["n"] == 0


def test_get_all_sessions_orders_newest_first(conn):
    db.insert_session(conn, make_summary(source_file="a.fit"), file_hash="a", session_type="run")
    db.insert_session(conn, make_summary(source_file="b.fit"), file_hash="b", session_type="run")

    rows = conn.execute(
        "UPDATE sessions SET start_time = ? WHERE file_hash = ?", ("2026-01-01T00:00:00", "a")
    )
    conn.execute("UPDATE sessions SET start_time = ? WHERE file_hash = ?", ("2026-06-01T00:00:00", "b"))
    conn.commit()

    sessions = db.get_all_sessions(conn)
    assert [s["file_hash"] for s in sessions] == ["b", "a"]


def test_backup_database_creates_and_prunes(tmp_path):
    db_path = tmp_path / "test.db"
    backup_dir = tmp_path / "backups"

    conn = db.get_connection(db_path)
    db.insert_session(conn, make_summary(), file_hash="x", session_type="run")
    conn.close()

    paths = []
    for _ in range(3):
        backup_path = db.backup_database(db_path, backup_dir, keep=2)
        paths.append(backup_path)
        time.sleep(0.01)  # ensure distinct timestamps

    remaining = sorted(backup_dir.glob("test_*.db"))
    assert len(remaining) == 2
    assert remaining[-1].name == paths[-1].name


def test_init_db_backs_up_before_applying_a_new_migration(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    backup_dir = tmp_path / "backups"

    conn = db.get_connection(db_path)
    db.insert_session(conn, make_summary(), file_hash="existing", session_type="run")
    conn.close()

    # Simulate a future migration being added after this database was created.
    monkeypatch.setattr(db, "MIGRATIONS", db.MIGRATIONS + [(2, "CREATE TABLE extra (id INTEGER PRIMARY KEY);")])

    conn = db.get_connection(db_path)
    version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
    assert version == 2
    assert db.session_exists(conn, "existing")

    assert list(backup_dir.glob("test_*.db"))


def test_get_session_by_id(conn):
    session_id = db.insert_session(conn, make_summary(), file_hash="one", session_type="run")

    row = db.get_session(conn, session_id)
    assert row["file_hash"] == "one"
    assert db.get_session(conn, session_id + 999) is None


def test_update_session_type(conn):
    session_id = db.insert_session(conn, make_summary(), file_hash="one", session_type="run")

    db.update_session_type(conn, session_id, "strength")

    assert db.get_session(conn, session_id)["session_type"] == "strength"


def test_get_splits_and_samples_ordered(conn):
    session_id = db.insert_session(conn, make_summary(), file_hash="one", session_type="run")
    db.insert_splits(
        conn,
        session_id,
        [
            SplitSummary(split_index=2, distance_km=1.0, duration_s=300.0, avg_pace_min_per_km=5.0, avg_heart_rate=140),
            SplitSummary(split_index=1, distance_km=1.0, duration_s=290.0, avg_pace_min_per_km=4.8, avg_heart_rate=145),
        ],
    )
    db.insert_samples(
        conn,
        session_id,
        [
            Sample(elapsed_s=5.0, distance_km=0.02, speed_m_s=3.3, heart_rate=132, cadence=80.0, altitude_m=10.0),
            Sample(elapsed_s=0.0, distance_km=0.0, speed_m_s=3.3, heart_rate=130, cadence=80.0, altitude_m=10.0),
        ],
    )

    splits = db.get_splits(conn, session_id)
    samples = db.get_samples(conn, session_id)

    assert [s["split_index"] for s in splits] == [1, 2]
    assert [s["elapsed_s"] for s in samples] == [0.0, 5.0]


def test_get_and_set_setting(conn):
    assert db.get_setting(conn, "inbox_folder") is None
    assert db.get_setting(conn, "inbox_folder", default="fallback") == "fallback"

    db.set_setting(conn, "inbox_folder", "C:/inbox")
    assert db.get_setting(conn, "inbox_folder") == "C:/inbox"

    db.set_setting(conn, "inbox_folder", "C:/other")
    assert db.get_setting(conn, "inbox_folder") == "C:/other"


def test_get_note_when_none_exists(conn):
    session_id = db.insert_session(conn, make_summary(), file_hash="one", session_type="run")
    assert db.get_note(conn, session_id) is None


def test_upsert_note_inserts_then_updates(conn):
    session_id = db.insert_session(conn, make_summary(), file_hash="one", session_type="strength")

    db.upsert_note(conn, session_id, rpe=7, note_text="Felt good", focus_tag="legs")
    note = db.get_note(conn, session_id)
    assert note["rpe"] == 7
    assert note["note_text"] == "Felt good"
    assert note["focus_tag"] == "legs"

    db.upsert_note(conn, session_id, rpe=8, note_text="Actually tough", focus_tag="legs")
    note = db.get_note(conn, session_id)
    assert note["rpe"] == 8
    assert note["note_text"] == "Actually tough"
    assert conn.execute("SELECT COUNT(*) AS n FROM notes").fetchone()["n"] == 1


def test_insert_and_get_niggles_for_session(conn):
    session_id = db.insert_session(conn, make_summary(), file_hash="one", session_type="run")

    db.insert_niggle(conn, session_id, location="ankle", side="left", severity=4)
    db.insert_niggle(conn, session_id, location="knee", side=None, severity=2)

    niggles = db.get_niggles_for_session(conn, session_id)
    assert len(niggles) == 2
    assert niggles[0]["location"] == "ankle"
    assert niggles[0]["side"] == "left"
    assert niggles[1]["location"] == "knee"
    assert niggles[1]["side"] is None


def test_delete_niggles_for_session(conn):
    session_id = db.insert_session(conn, make_summary(), file_hash="one", session_type="run")
    db.insert_niggle(conn, session_id, location="ankle", side="left", severity=4)

    db.delete_niggles_for_session(conn, session_id)

    assert db.get_niggles_for_session(conn, session_id) == []


def test_get_all_niggles_with_dates_orders_newest_session_first(conn):
    old_session = db.insert_session(conn, make_summary(start_time=datetime(2026, 1, 1, tzinfo=timezone.utc)), file_hash="old", session_type="run")
    new_session = db.insert_session(conn, make_summary(start_time=datetime(2026, 6, 1, tzinfo=timezone.utc)), file_hash="new", session_type="run")

    db.insert_niggle(conn, old_session, location="ankle", side="left", severity=3)
    db.insert_niggle(conn, new_session, location="knee", side="right", severity=5)

    rows = db.get_all_niggles_with_dates(conn)

    assert [r["location"] for r in rows] == ["knee", "ankle"]
    assert rows[0]["session_start_time"] == "2026-06-01T00:00:00+00:00"
