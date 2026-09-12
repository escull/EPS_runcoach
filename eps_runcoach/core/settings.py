"""Read/write user settings, stored as key/value pairs in the database.

Only `inbox_folder` exists so far. More keys (max HR, resting HR, 5k goal,
AI model name) get added in later phases — plain string keys are enough
until then, so no per-setting accessor functions yet.
"""

from __future__ import annotations

import sqlite3

from eps_runcoach.core import db

INBOX_FOLDER_KEY = "inbox_folder"


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    return db.get_setting(conn, key, default)


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    db.set_setting(conn, key, value)
