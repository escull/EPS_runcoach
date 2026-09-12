"""Read/write user settings, stored as key/value pairs in the database.

AI model name gets added in a later phase — plain string keys are enough
until then, so no per-setting accessor functions beyond the generic
get_setting/set_setting.
"""

from __future__ import annotations

import sqlite3

from eps_runcoach.core import db

INBOX_FOLDER_KEY = "inbox_folder"
MAX_HEART_RATE_KEY = "max_heart_rate"
RESTING_HEART_RATE_KEY = "resting_heart_rate"
GOAL_5K_SECONDS_KEY = "goal_5k_seconds"

DEFAULT_GOAL_5K_SECONDS = 1500.0  # sub-25 minutes


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    return db.get_setting(conn, key, default)


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    db.set_setting(conn, key, value)
