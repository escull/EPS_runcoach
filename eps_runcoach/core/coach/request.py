"""Orchestrates coaching requests: build the context, ask the provider
for a review, and save the result. Nothing is saved if a request fails.

Two flavours:
- request_review: a single session's advice (Session Detail's Regenerate).
- request_insights: a holistic "catch-up" review covering everything
  since the coach was last consulted (the AI Insights page).
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from eps_runcoach.core import db, metrics
from eps_runcoach.core import settings as core_settings
from eps_runcoach.core.coach.base import CoachError, CoachProvider
from eps_runcoach.core.coach.context import build_context
from eps_runcoach.core.coach.gemini import GeminiProvider

SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.md"
QUESTION_SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt_question.md"


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _load_question_system_prompt() -> str:
    return QUESTION_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _get_model(conn: sqlite3.Connection) -> str:
    return core_settings.get_setting(
        conn, core_settings.AI_MODEL_NAME_KEY, default=core_settings.DEFAULT_AI_MODEL_NAME
    )


def request_review(
    conn: sqlite3.Connection,
    session_id: int,
    provider: CoachProvider | None = None,
    provider_name: str = "gemini",
) -> str:
    """Build context, ask the coach to review one specific session, save
    it, and return the review text. Raises a CoachError (or subclass) on
    failure.
    """
    model = _get_model(conn)
    if provider is None:
        provider = GeminiProvider(model)

    context = build_context(conn)
    system_prompt = _load_system_prompt()
    review_text = provider.generate_review(context, system_prompt)

    db.insert_ai_review(conn, session_id, provider=provider_name, model=model, review_text=review_text)
    return review_text


def request_insights(
    conn: sqlite3.Connection,
    provider: CoachProvider | None = None,
    provider_name: str = "gemini",
) -> str:
    """Ask the coach for a holistic review of everything since it was
    last consulted (or the last `metrics.FITNESS_SPAN_DAYS` days, if
    never consulted before). Saved against the most recent session, since
    a review isn't tied to just one. Raises a CoachError if there are no
    sessions to review, or on any provider failure.
    """
    sessions = db.get_all_sessions(conn)
    if not sessions:
        raise CoachError("Import some sessions before requesting insights.")

    latest_review = db.get_latest_ai_review(conn)
    if latest_review is not None:
        since = datetime.fromisoformat(latest_review["created_at"]).date()
    else:
        since = date.today() - timedelta(days=metrics.FITNESS_SPAN_DAYS)

    model = _get_model(conn)
    if provider is None:
        provider = GeminiProvider(model)

    context = build_context(conn, since=since)
    system_prompt = _load_system_prompt()
    review_text = provider.generate_review(context, system_prompt)

    most_recent_session_id = sessions[0]["id"]  # get_all_sessions orders newest first
    db.insert_ai_review(conn, most_recent_session_id, provider=provider_name, model=model, review_text=review_text)
    return review_text


def request_question(
    conn: sqlite3.Connection,
    question: str,
    provider: CoachProvider | None = None,
    provider_name: str = "gemini",
) -> str:
    """Ask the coach a one-off question, using the same compact training
    context as a review so it can answer with actual knowledge of recent
    training. Saved against the most recent session, like insights, since
    a question isn't tied to one specific session. Raises a CoachError if
    there are no sessions yet, or on any provider failure.
    """
    sessions = db.get_all_sessions(conn)
    if not sessions:
        raise CoachError("Import some sessions before asking the coach a question.")

    model = _get_model(conn)
    if provider is None:
        provider = GeminiProvider(model)

    context = build_context(conn)
    context_with_question = f"{context}\n\n=== My question ===\n{question}"
    system_prompt = _load_question_system_prompt()
    answer_text = provider.generate_review(context_with_question, system_prompt)

    review_text = f"Q: {question}\n\n{answer_text}"
    most_recent_session_id = sessions[0]["id"]
    db.insert_ai_review(conn, most_recent_session_id, provider=provider_name, model=model, review_text=review_text)
    return review_text
