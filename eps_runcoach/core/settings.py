"""Read/write user settings, stored as key/value pairs in the database."""

from __future__ import annotations

import sqlite3

from eps_runcoach.core import db

INBOX_FOLDER_KEY = "inbox_folder"
MAX_HEART_RATE_KEY = "max_heart_rate"
RESTING_HEART_RATE_KEY = "resting_heart_rate"
GOAL_5K_SECONDS_KEY = "goal_5k_seconds"
AI_MODEL_NAME_KEY = "ai_model_name"

DEFAULT_GOAL_5K_SECONDS = 1500.0  # sub-25 minutes
DEFAULT_AI_MODEL_NAME = "gemini-3.8-flash"


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    return db.get_setting(conn, key, default)


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    db.set_setting(conn, key, value)
