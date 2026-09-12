"""Reads and writes the Gemini API key in .env - the one place it lives,
per the project's secrets rule. Lets the Settings page offer a field
instead of requiring the file to be hand-edited.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import get_key, set_key

ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
PLACEHOLDER = "paste-your-key-here"


def get_api_key(env_path: Path = ENV_PATH) -> str:
    if not env_path.exists():
        return ""
    value = get_key(str(env_path), "GEMINI_API_KEY") or ""
    return "" if value == PLACEHOLDER else value


def set_api_key(value: str, env_path: Path = ENV_PATH) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        env_path.touch()
    set_key(str(env_path), "GEMINI_API_KEY", value)
    os.environ["GEMINI_API_KEY"] = value  # takes effect immediately, no restart needed
