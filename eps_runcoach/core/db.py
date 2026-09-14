"""All SQL for EPS RunCoach lives here: schema, migrations, connections,
backups, and the insert/query functions every other module uses to talk to
the database. Nothing outside this file should run SQL directly.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from eps_runcoach.core import app_paths
from eps_runcoach.core.fit_import import Sample, SessionSummary, SplitSummary

DEFAULT_DB_PATH = app_paths.get_data_dir() / "eps_runcoach.db"
MAX_BACKUPS = 10

# Each migration is (version, sql). Applied once, in order, each in its own
# transaction. Never edit a migration once it's been committed — append a
# new one instead, so nobody's existing data is dropped or reinterpreted.
MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_hash TEXT NOT NULL UNIQUE,
            source_file TEXT NOT NULL,
            sport TEXT NOT NULL,
            sub_sport TEXT,
            session_type TEXT NOT NULL,
            start_time TEXT NOT NULL,
            duration_s REAL,
            distance_km REAL,
            avg_pace_min_per_km REAL,
            avg_heart_rate INTEGER,
            max_heart_rate INTEGER,
            calories INTEGER,
            total_ascent REAL,
            total_descent REAL,
            avg_cadence REAL,
            imported_at TEXT NOT NULL
        );

        CREATE TABLE splits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            split_index INTEGER NOT NULL,
            distance_km REAL,
            duration_s REAL,
            avg_pace_min_per_km REAL,
            avg_heart_rate INTEGER
        );

        CREATE TABLE samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            elapsed_s REAL NOT NULL,
            distance_km REAL,
            speed_m_s REAL,
            heart_rate INTEGER,
            cadence REAL,
            altitude_m REAL
        );

        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
            rpe INTEGER,
            note_text TEXT,
            focus_tag TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE niggles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            location TEXT NOT NULL,
            side TEXT,
            severity INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE ai_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            review_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX idx_splits_session_id ON splits(session_id);
        CREATE INDEX idx_samples_session_id ON samples(session_id);
        CREATE INDEX idx_niggles_session_id ON niggles(session_id);
        CREATE INDEX idx_ai_reviews_session_id ON ai_reviews(session_id);
        """,
    ),
    (
        2,
        """
        ALTER TABLE sessions ADD COLUMN estimated_vo2_max REAL;
        ALTER TABLE sessions ADD COLUMN recovery_time_s REAL;
        ALTER TABLE sessions ADD COLUMN total_training_effect REAL;
        """,
    ),
    (
        3,
        """
        CREATE TABLE body_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_date TEXT NOT NULL,
            weight_kg REAL,
            body_fat_pct REAL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX idx_body_metrics_recorded_date ON body_metrics(recorded_date);
        """,
    ),
]


def get_db_path(conn: sqlite3.Connection) -> Path:
    """Return the file path of the database a connection is attached to."""
    row = conn.execute("PRAGMA database_list").fetchone()
    return Path(row[2])


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection with foreign keys enforced, creating the schema (or
    applying any pending migrations) first if needed.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    init_db(conn, db_path)
    return conn


def init_db(conn: sqlite3.Connection, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Ensure schema_version exists, then apply any migrations newer than
    the current version. Backs up the database first if there's anything
    to migrate and the file already holds data.
    """
    db_path = Path(db_path)
    # Checked before anything below writes to the file — CREATE TABLE commits
    # immediately and would otherwise make every brand-new database look
    # "existing" by the time we got round to checking.
    db_had_existing_data = db_path.exists() and db_path.stat().st_size > 0

    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (0)")
        conn.commit()
        current_version = 0
    else:
        current_version = row["version"]

    pending = [m for m in MIGRATIONS if m[0] > current_version]
    if not pending:
        return

    if db_had_existing_data:
        backup_database(db_path)

    for version, sql in pending:
        conn.executescript(sql)
        conn.execute("UPDATE schema_version SET version = ?", (version,))
        conn.commit()


def backup_database(
    db_path: str | Path = DEFAULT_DB_PATH,
    backup_dir: str | Path | None = None,
    keep: int = MAX_BACKUPS,
) -> Path | None:
    """Copy the database file into backup_dir (default: a `backups` folder
    next to the database itself) with a timestamped name, then prune to the
    most recent `keep` backups. Returns the backup path, or None if there
    was no database file to back up.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        return None

    backup_dir = Path(backup_dir) if backup_dir is not None else db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    backup_path = backup_dir / f"{db_path.stem}_{timestamp}.db"
    shutil.copy2(db_path, backup_path)

    backups = sorted(backup_dir.glob(f"{db_path.stem}_*.db"))
    for old_backup in backups[:-keep]:
        old_backup.unlink()

    return backup_path


def session_exists(conn: sqlite3.Connection, file_hash: str) -> bool:
    row = conn.execute("SELECT 1 FROM sessions WHERE file_hash = ?", (file_hash,)).fetchone()
    return row is not None


def get_session_by_hash(conn: sqlite3.Connection, file_hash: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM sessions WHERE file_hash = ?", (file_hash,)).fetchone()


def get_all_sessions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM sessions ORDER BY start_time DESC").fetchall()


def get_session(conn: sqlite3.Connection, session_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()


def get_max_observed_heart_rate(conn: sqlite3.Connection) -> int | None:
    """Highest max_heart_rate recorded across all sessions - used to suggest
    a starting value for the max heart rate setting, since Suunto FIT files
    don't carry a separate stored physiological max HR.
    """
    row = conn.execute("SELECT MAX(max_heart_rate) AS value FROM sessions").fetchone()
    return row["value"] if row else None


def update_session_type(conn: sqlite3.Connection, session_id: int, session_type: str) -> None:
    conn.execute("UPDATE sessions SET session_type = ? WHERE id = ?", (session_type, session_id))
    conn.commit()


def get_splits(conn: sqlite3.Connection, session_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM splits WHERE session_id = ? ORDER BY split_index", (session_id,)
    ).fetchall()


def get_samples(conn: sqlite3.Connection, session_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM samples WHERE session_id = ? ORDER BY elapsed_s", (session_id,)
    ).fetchall()


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row is not None else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


def get_note(conn: sqlite3.Connection, session_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM notes WHERE session_id = ?", (session_id,)).fetchone()


def upsert_note(
    conn: sqlite3.Connection,
    session_id: int,
    rpe: int | None,
    note_text: str | None,
    focus_tag: str | None,
) -> None:
    """Insert or update the single note row for a session."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO notes (session_id, rpe, note_text, focus_tag, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            rpe = excluded.rpe,
            note_text = excluded.note_text,
            focus_tag = excluded.focus_tag,
            updated_at = excluded.updated_at
        """,
        (session_id, rpe, note_text, focus_tag, now, now),
    )
    conn.commit()


def get_niggles_for_session(conn: sqlite3.Connection, session_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM niggles WHERE session_id = ? ORDER BY id", (session_id,)
    ).fetchall()


def delete_niggles_for_session(conn: sqlite3.Connection, session_id: int) -> None:
    conn.execute("DELETE FROM niggles WHERE session_id = ?", (session_id,))
    conn.commit()


def insert_niggle(
    conn: sqlite3.Connection,
    session_id: int,
    location: str,
    side: str | None,
    severity: int,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO niggles (session_id, location, side, severity, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, location, side, severity, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def get_all_niggles_with_dates(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """All niggles joined with their session's start_time, newest session first
    - used for both the severity-over-time chart and the recent-entries list.
    """
    return conn.execute(
        """
        SELECT niggles.*, sessions.start_time AS session_start_time
        FROM niggles
        JOIN sessions ON sessions.id = niggles.session_id
        ORDER BY sessions.start_time DESC
        """
    ).fetchall()


def insert_body_metric(
    conn: sqlite3.Connection,
    recorded_date: str,
    weight_kg: float | None,
    body_fat_pct: float | None = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO body_metrics (recorded_date, weight_kg, body_fat_pct, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (recorded_date, weight_kg, body_fat_pct, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def get_all_body_metrics(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM body_metrics ORDER BY recorded_date").fetchall()


def insert_session(
    conn: sqlite3.Connection,
    summary: SessionSummary,
    file_hash: str,
    session_type: str,
) -> int:
    """Insert one session row and return its new id."""
    cursor = conn.execute(
        """
        INSERT INTO sessions (
            file_hash, source_file, sport, sub_sport, session_type,
            start_time, duration_s, distance_km, avg_pace_min_per_km,
            avg_heart_rate, max_heart_rate, calories, total_ascent,
            total_descent, avg_cadence, imported_at, estimated_vo2_max,
            recovery_time_s, total_training_effect
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            file_hash,
            summary.source_file,
            summary.sport,
            summary.sub_sport,
            session_type,
            summary.start_time.isoformat() if summary.start_time else None,
            summary.total_duration_s,
            summary.total_distance_km,
            summary.avg_pace_min_per_km,
            summary.avg_heart_rate,
            summary.max_heart_rate,
            summary.calories,
            summary.total_ascent,
            summary.total_descent,
            summary.avg_cadence,
            datetime.now(timezone.utc).isoformat(),
            summary.estimated_vo2_max,
            summary.recovery_time_s,
            summary.total_training_effect,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def insert_splits(conn: sqlite3.Connection, session_id: int, splits: list[SplitSummary]) -> None:
    conn.executemany(
        """
        INSERT INTO splits (
            session_id, split_index, distance_km, duration_s,
            avg_pace_min_per_km, avg_heart_rate
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                session_id,
                split.split_index,
                split.distance_km,
                split.duration_s,
                split.avg_pace_min_per_km,
                split.avg_heart_rate,
            )
            for split in splits
        ],
    )
    conn.commit()


def insert_samples(conn: sqlite3.Connection, session_id: int, samples: list[Sample]) -> None:
    conn.executemany(
        """
        INSERT INTO samples (
            session_id, elapsed_s, distance_km, speed_m_s, heart_rate,
            cadence, altitude_m
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                session_id,
                sample.elapsed_s,
                sample.distance_km,
                sample.speed_m_s,
                sample.heart_rate,
                sample.cadence,
                sample.altitude_m,
            )
            for sample in samples
        ],
    )
    conn.commit()


def insert_ai_review(conn: sqlite3.Connection, session_id: int, provider: str, model: str, review_text: str) -> int:
    cursor = conn.execute(
        """
        INSERT INTO ai_reviews (session_id, provider, model, review_text, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, provider, model, review_text, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def get_latest_ai_review_for_session(conn: sqlite3.Connection, session_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM ai_reviews WHERE session_id = ? ORDER BY created_at DESC, id DESC LIMIT 1",
        (session_id,),
    ).fetchone()


def get_latest_ai_review(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """The single most recent review across all sessions - used for the
    Dashboard's "Latest advice" panel.
    """
    return conn.execute("SELECT * FROM ai_reviews ORDER BY created_at DESC, id DESC LIMIT 1").fetchone()


def get_all_ai_reviews(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every review ever generated, newest first - used for the AI
    Insights page's history list.
    """
    return conn.execute("SELECT * FROM ai_reviews ORDER BY created_at DESC, id DESC").fetchall()
