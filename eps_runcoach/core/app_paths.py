"""Where the app's data lives: the project's data/ folder during
development, or a per-user AppData folder once packaged with PyInstaller
(sys.frozen) - a shipped .exe shouldn't need write access next to itself,
and data needs to survive being rebuilt/reinstalled in place.

Pure path computation only - no directory creation here. Callers already
create directories lazily where they're actually used (e.g. db.py's
get_connection, api_key.py's set_api_key).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DATA_FOLDER_NAME = "EPS RunCoach"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def get_data_dir() -> Path:
    if is_frozen():
        return Path(os.environ["APPDATA"]) / APP_DATA_FOLDER_NAME
    return Path("data")


def get_env_path() -> Path:
    if is_frozen():
        return get_data_dir() / ".env"
    return Path(__file__).resolve().parents[2] / ".env"


def get_resource_path(relative_path: str) -> Path:
    """A bundled read-only asset (e.g. assets/icon.ico) - PyInstaller
    extracts these under sys._MEIPASS (both onefile and onedir); in dev
    it's just the project root.
    """
    if is_frozen():
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[2]
    return base / relative_path
