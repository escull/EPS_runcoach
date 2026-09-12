"""Orchestrates a single coaching request: build the context, ask the
provider for a review, and save the result. Nothing is saved if the
request fails.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from eps_runcoach.core import db
from eps_runcoach.core import settings as core_settings
from eps_runcoach.core.coach.base import CoachProvider
from eps_runcoach.core.coach.context import build_context
from eps_runcoach.core.coach.gemini import GeminiProvider

SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.md"


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def request_review(
    conn: sqlite3.Connection,
    session_id: int,
    provider: CoachProvider | None = None,
    provider_name: str = "gemini",
) -> str:
    """Build context, ask the coach for a review, save it, and return the
    review text. Raises a CoachError (or subclass) on failure.
    """
    model = core_settings.get_setting(
        conn, core_settings.AI_MODEL_NAME_KEY, default=core_settings.DEFAULT_AI_MODEL_NAME
    )
    if provider is None:
        provider = GeminiProvider(model)

    context = build_context(conn)
    system_prompt = _load_system_prompt()
    review_text = provider.generate_review(context, system_prompt)

    db.insert_ai_review(conn, session_id, provider=provider_name, model=model, review_text=review_text)
    return review_text
