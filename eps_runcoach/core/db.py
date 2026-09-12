"""All SQL for EPS RunCoach lives here: schema, migrations, connections,
backups, and the insert/query functions every other module uses to talk to
the database. Nothing outside this file should run SQL directly.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from eps_runcoach.core.fit_import import Sample, SessionSummary, SplitSummary

DEFAULT_DB_PATH = Path("data/eps_runcoach.db")
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
            total_descent, avg_cadence, imported_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
