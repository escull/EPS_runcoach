"""Imports FIT files into the database: hashing for dedupe, a backup before
each import batch, and per-file error handling so one bad file never aborts
the rest of an import.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from eps_runcoach.core import db
from eps_runcoach.core.fit_import import classify_session_type, parse_fit_file


@dataclass
class ImportSummary:
    imported: list[tuple[str, int]] = field(default_factory=list)  # (filename, session_id)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_files(paths: list[str | Path], conn: sqlite3.Connection) -> ImportSummary:
    """Import each FIT file in `paths` into the database behind `conn`.

    Backs up the database once before the batch. Each file is hashed to
    skip anything already imported, then parsed and inserted; a file that
    can't be read or doesn't parse as a valid FIT file is recorded under
    `failed` with a reason rather than raising, so one bad file doesn't
    stop the rest of the batch.
    """
    summary = ImportSummary()
    db.backup_database(db.get_db_path(conn))

    for raw_path in paths:
        path = Path(raw_path)

        try:
            file_hash = _hash_file(path)
        except OSError as exc:
            summary.failed.append((path.name, f"couldn't read file: {exc}"))
            continue

        if db.session_exists(conn, file_hash):
            summary.skipped.append((path.name, "duplicate (already imported)"))
            continue

        try:
            parsed = parse_fit_file(path)
        except Exception as exc:  # noqa: BLE001 - any bad/unusual FIT file must not crash the import
            summary.failed.append((path.name, f"couldn't parse FIT file: {exc}"))
            continue

        session_type = classify_session_type(parsed.summary.sport, parsed.summary.sub_sport)
        session_id = db.insert_session(conn, parsed.summary, file_hash=file_hash, session_type=session_type)
        db.insert_splits(conn, session_id, parsed.splits)
        db.insert_samples(conn, session_id, parsed.samples)
        summary.imported.append((path.name, session_id))

    return summary


def import_folder(folder: str | Path, conn: sqlite3.Connection) -> ImportSummary:
    """Import every .fit file found directly inside `folder`."""
    fit_files = sorted(Path(folder).glob("*.fit"))
    return import_files(fit_files, conn)
