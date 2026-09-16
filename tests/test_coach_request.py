from datetime import datetime, timezone

import pytest

from eps_runcoach.core import db
from eps_runcoach.core.coach.base import CoachConnectionError, CoachError, CoachProvider
from eps_runcoach.core.coach.request import request_insights, request_question, request_review
from eps_runcoach.core.fit_import import SessionSummary


class FakeProvider(CoachProvider):
    def __init__(self, response: str | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.received_context = None
        self.received_system_prompt = None

    def generate_review(self, context: str, system_prompt: str) -> str:
        self.received_context = context
        self.received_system_prompt = system_prompt
        if self.error is not None:
            raise self.error
        return self.response


def make_summary(**overrides) -> SessionSummary:
    defaults = dict(
        sport="running",
        sub_sport="treadmill",
        start_time=datetime(2026, 9, 5, tzinfo=timezone.utc),
        total_distance_km=5.0,
        total_duration_s=1500.0,
        avg_heart_rate=140,
        max_heart_rate=160,
        avg_pace_min_per_km=5.0,
        calories=400,
        total_ascent=0.0,
        total_descent=0.0,
        avg_cadence=80.0,
        source_file="test.fit",
    )
    defaults.update(overrides)
    return SessionSummary(**defaults)


def test_request_review_saves_successful_response(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    session_id = db.insert_session(conn, make_summary(), file_hash="a", session_type="run")
    fake = FakeProvider(response="Nice session - recover easy tomorrow.")

    result = request_review(conn, session_id, provider=fake)

    assert result == "Nice session - recover easy tomorrow."
    saved = db.get_latest_ai_review_for_session(conn, session_id)
    assert saved["review_text"] == "Nice session - recover easy tomorrow."
    assert saved["provider"] == "gemini"
    assert fake.received_context  # context text was actually passed through
    assert "pain" in fake.received_system_prompt.lower()  # sanity check it's the real prompt file


def test_request_review_propagates_error_and_saves_nothing(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    session_id = db.insert_session(conn, make_summary(), file_hash="a", session_type="run")
    fake = FakeProvider(error=CoachConnectionError("no internet"))

    with pytest.raises(CoachConnectionError):
        request_review(conn, session_id, provider=fake)

    assert db.get_latest_ai_review_for_session(conn, session_id) is None


def test_request_insights_requires_at_least_one_session(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    fake = FakeProvider(response="shouldn't be called")

    with pytest.raises(CoachError):
        request_insights(conn, provider=fake)

    assert fake.received_context is None


def test_request_insights_saves_against_most_recent_session(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    older_id = db.insert_session(
        conn, make_summary(start_time=datetime(2026, 9, 1, tzinfo=timezone.utc)), file_hash="a", session_type="run"
    )
    newer_id = db.insert_session(
        conn, make_summary(start_time=datetime(2026, 9, 5, tzinfo=timezone.utc)), file_hash="b", session_type="run"
    )
    fake = FakeProvider(response="Here's how the last few sessions went overall.")

    result = request_insights(conn, provider=fake)

    assert result == "Here's how the last few sessions went overall."
    assert db.get_latest_ai_review_for_session(conn, newer_id) is not None
    assert db.get_latest_ai_review_for_session(conn, older_id) is None


def test_request_insights_uses_since_last_review_as_the_window(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    session_id = db.insert_session(
        conn, make_summary(start_time=datetime(2026, 9, 1, tzinfo=timezone.utc)), file_hash="a", session_type="run"
    )
    db.insert_ai_review(conn, session_id, provider="gemini", model="gemini-3.8-flash", review_text="first check-in")

    fake = FakeProvider(response="second check-in")
    request_insights(conn, provider=fake)

    assert "since" in fake.received_context.lower()


def test_request_question_requires_at_least_one_session(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    fake = FakeProvider(response="shouldn't be called")

    with pytest.raises(CoachError):
        request_question(conn, "What should I eat before a long run?", provider=fake)

    assert fake.received_context is None


def test_request_question_includes_the_question_in_context_and_saved_answer(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    session_id = db.insert_session(conn, make_summary(), file_hash="a", session_type="run")
    fake = FakeProvider(response="Have a small carb-heavy snack an hour or two before.")

    result = request_question(conn, "What should I eat before a long run?", provider=fake)

    assert "What should I eat before a long run?" in fake.received_context
    assert "pain" in fake.received_system_prompt.lower()  # the question-specific prompt, still safety-conscious
    assert result.startswith("Q: What should I eat before a long run?")
    assert "Have a small carb-heavy snack" in result

    saved = db.get_latest_ai_review_for_session(conn, session_id)
    assert saved["review_text"] == result


def test_request_question_propagates_error_and_saves_nothing(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    session_id = db.insert_session(conn, make_summary(), file_hash="a", session_type="run")
    fake = FakeProvider(error=CoachConnectionError("no internet"))

    with pytest.raises(CoachConnectionError):
        request_question(conn, "Any tips for hills?", provider=fake)

    assert db.get_latest_ai_review_for_session(conn, session_id) is None
