"""Appends unexpected errors to a log file in the data directory.

The packaged app is windowed (no console), so an unhandled exception
normally just vanishes - nothing is visible anywhere. This gives every
failure somewhere to land, so a "why did this hang/fail" report from a
packaged build is actually diagnosable.
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone
from pathlib import Path

from eps_runcoach.core import app_paths

LOG_PATH = app_paths.get_data_dir() / "error.log"


def log_exception(context: str) -> Path:
    """Append the current exception's traceback under `context` (e.g.
    "AI Insights request"). Must be called from an except block. Returns
    the log file path.
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"\n=== {timestamp} - {context} ===\n")
        f.write(traceback.format_exc())
    return LOG_PATH
